#include "kaidi_desk.h"

#include <cmath>

#include "esphome/core/log.h"

namespace esphome {
namespace kaidi_desk {

static const char *const TAG = "kaidi_desk";

static const uint8_t FRAME_START = 0x68;
static const uint8_t FRAME_ADDRESS = 0x01;
static const uint8_t FRAME_END = 0x16;
static const uint32_t AWAKE_FRESH_MS = 150;
static const uint32_t ASLEEP_AFTER_MS = 2000;
static const uint32_t HEIGHT_STALE_MS = 3000;
static const uint32_t WAKE_HOLD_MS = 500;
static const uint8_t RELEASE_IDLE_FRAMES = 3;
static const uint32_t KEEPALIVE_INTERVAL_MS = 10000;
static const uint8_t KEEPALIVE_FRAMES = 3;

void KaidiDesk::setup() {
  if (this->tx_enable_pin_ != nullptr) {
    this->tx_enable_pin_->setup();
    this->tx_enable_pin_->digital_write(false);
  }
  if (this->wake_pin_ != nullptr) {
    this->wake_pin_->setup();
    this->wake_pin_->digital_write(false);
  }
  if (this->keypad_sense_pin_ != nullptr) {
    this->keypad_sense_pin_->setup();
    this->keypad_sense_pin_->attach_interrupt(&KaidiDesk::keypad_isr_, this, gpio::INTERRUPT_FALLING_EDGE);
  }
}

void IRAM_ATTR KaidiDesk::keypad_isr_(KaidiDesk *desk) {
  if (!desk->transmitting_)
    desk->keypad_edge_ = true;
}

void KaidiDesk::dump_config() {
  ESP_LOGCONFIG(TAG, "Kaidi Desk:");
  LOG_PIN("  TX Enable Pin: ", this->tx_enable_pin_);
  LOG_PIN("  Wake Pin: ", this->wake_pin_);
  LOG_PIN("  Keypad Sense Pin: ", this->keypad_sense_pin_);
  ESP_LOGCONFIG(TAG, "  Frame Interval: %" PRIu32 " ms", this->frame_interval_);
  ESP_LOGCONFIG(TAG, "  Wake Settle: %" PRIu32 " ms", this->wake_settle_);
  ESP_LOGCONFIG(TAG, "  Nudge Duration: %" PRIu32 " ms", this->nudge_duration_);
  ESP_LOGCONFIG(TAG, "  Tolerance: %.1f cm", this->tolerance_);
  ESP_LOGCONFIG(TAG, "  Coast: %.1f cm", this->coast_);
  LOG_SENSOR("  ", "Height", this->height_sensor_);
  LOG_TEXT_SENSOR("  ", "Status", this->status_sensor_);
  LOG_NUMBER("  ", "Target Height", this->target_number_);
  this->check_uart_settings(9600);
}

void KaidiDesk::loop() {
  this->read_frames_();
  uint32_t now = millis();

  if (this->keypad_edge_) {
    this->keypad_edge_ = false;
    if (this->state_ != State::IDLE)
      this->abort_for_keypad_();
  }

  if (this->state_ == State::IDLE) {
    if (this->box_mode_ != BOX_MODE_NONE && now - this->last_rx_ms_ > ASLEEP_AFTER_MS) {
      this->box_mode_ = BOX_MODE_NONE;
      this->publish_status_("Asleep");
    }
    this->keep_alive_(now);
    return;
  }
  if (now - this->last_tx_ms_ < this->frame_interval_)
    return;

  switch (this->state_) {
    case State::WAKING:
      if (this->box_awake_(now)) {
        this->state_ = State::ACTING;
        this->state_since_ms_ = now;
        this->reset_seen_ = false;
        this->step_action_(now);
      } else if (now - this->state_since_ms_ > this->wake_timeout_) {
        ESP_LOGW(TAG, "Box did not answer within %" PRIu32 " ms", this->wake_timeout_);
        this->release_();
      } else {
        this->send_(COMMAND_IDLE);
      }
      break;
    case State::ACTING:
      this->step_action_(now);
      break;
    case State::RELEASING:
      if (this->release_frames_ > 0) {
        this->send_(COMMAND_IDLE);
        this->release_frames_--;
      } else if (now - this->last_tx_ms_ >= WAKE_HOLD_MS) {
        this->finish_();
      }
      break;
    default:
      break;
  }
}

void KaidiDesk::step_action_(uint32_t now) {
  uint32_t elapsed = now - this->state_since_ms_;
  switch (this->action_) {
    case Action::MOVE: {
      if (std::isnan(this->height_) || now - this->height_ms_ > HEIGHT_STALE_MS) {
        ESP_LOGW(TAG, "Height feedback went stale, stopping");
        this->release_();
        return;
      }
      if (elapsed > this->move_timeout_) {
        ESP_LOGW(TAG, "Move took longer than %" PRIu32 " ms, stopping", this->move_timeout_);
        this->release_();
        return;
      }
      float remaining = this->moving_up_ ? this->target_ - this->height_ : this->height_ - this->target_;
      if (std::fabs(this->height_ - this->target_) <= this->tolerance_ || remaining <= this->coast_) {
        this->release_();
        return;
      }
      this->send_(this->moving_up_ ? COMMAND_UP : COMMAND_DOWN);
      return;
    }
    case Action::NUDGE_UP:
    case Action::NUDGE_DOWN:
      if (elapsed >= this->nudge_duration_) {
        this->release_();
        return;
      }
      this->send_(this->action_ == Action::NUDGE_UP ? COMMAND_UP : COMMAND_DOWN);
      return;
    case Action::RESET:
      if (this->box_mode_ == BOX_MODE_RESET_NEEDED || this->box_mode_ == BOX_MODE_REBOUND)
        this->reset_seen_ = true;
      if (this->reset_seen_ && this->box_mode_ == BOX_MODE_HEIGHT) {
        this->release_();
        return;
      }
      if (!this->reset_seen_ && elapsed > 5000) {
        ESP_LOGW(TAG, "Box never entered its reset, stopping");
        this->release_();
        return;
      }
      if (elapsed > this->reset_timeout_) {
        ESP_LOGW(TAG, "Reset did not finish within %" PRIu32 " ms, stopping", this->reset_timeout_);
        this->release_();
        return;
      }
      this->send_(COMMAND_RESET);
      return;
    default:
      this->release_();
      return;
  }
}

void KaidiDesk::read_frames_() {
  uint8_t byte;
  while (this->available() > 0 && this->read_byte(&byte)) {
    if (this->buffer_len_ == 0 && byte != FRAME_START)
      continue;
    this->buffer_[this->buffer_len_++] = byte;
    if (this->buffer_len_ < sizeof(this->buffer_))
      continue;
    this->buffer_len_ = 0;
    const uint8_t *p = this->buffer_;
    uint8_t checksum = p[1] + p[2] + p[3] + p[4];
    if (p[1] != FRAME_ADDRESS || p[5] != checksum || p[6] != FRAME_END) {
      ESP_LOGV(TAG, "Dropped malformed frame");
      continue;
    }
    this->handle_frame_(p[2], (p[3] << 8) | p[4]);
  }
}

void KaidiDesk::handle_frame_(uint8_t mode, uint16_t value) {
  uint32_t now = millis();
  if (now - this->last_rx_ms_ > 300)
    this->awake_since_ms_ = now;
  this->last_rx_ms_ = now;

  if (mode != this->box_mode_) {
    this->box_mode_ = mode;
    switch (mode) {
      case BOX_MODE_HEIGHT:
        this->publish_status_("Ready");
        break;
      case BOX_MODE_RESET_NEEDED:
        this->publish_status_("Reset Needed");
        break;
      case BOX_MODE_REBOUND:
        this->publish_status_("Resetting");
        break;
      default:
        ESP_LOGD(TAG, "Unknown box mode 0x%02X", mode);
        this->publish_status_("Unknown");
        break;
    }
  }
  if (mode != BOX_MODE_HEIGHT)
    return;

  this->height_ = value / 10.0f;
  this->height_ms_ = now;
  if (this->height_sensor_ != nullptr && this->height_ != this->published_height_) {
    this->published_height_ = this->height_;
    this->height_sensor_->publish_state(this->height_);
  }
  if (this->state_ == State::IDLE)
    this->sync_target_();
}

void KaidiDesk::send_(Command command) {
  const uint8_t frame[7] = {FRAME_START, FRAME_ADDRESS, command, 0x00, 0x00,
                            static_cast<uint8_t>(FRAME_ADDRESS + command), FRAME_END};
  this->transmitting_ = true;
  if (this->tx_enable_pin_ != nullptr)
    this->tx_enable_pin_->digital_write(true);
  this->write_array(frame, sizeof(frame));
  this->flush();
  if (this->tx_enable_pin_ != nullptr)
    this->tx_enable_pin_->digital_write(false);
  this->transmitting_ = false;
  this->last_tx_ms_ = millis();
}

void KaidiDesk::begin_(Action action) {
  this->action_ = action;
  this->state_ = State::WAKING;
  this->state_since_ms_ = millis();
  this->apply_wake_pin_();
  this->high_freq_.start();
}

void KaidiDesk::release_() {
  this->state_ = State::RELEASING;
  this->release_frames_ = RELEASE_IDLE_FRAMES;
}

void KaidiDesk::abort_for_keypad_() {
  ESP_LOGI(TAG, "Keypad pressed, handing the desk back to it");
  this->finish_();
}

void KaidiDesk::finish_() {
  this->state_ = State::IDLE;
  this->action_ = Action::NONE;
  this->apply_wake_pin_();
  this->high_freq_.stop();
  this->sync_target_();
}

bool KaidiDesk::box_awake_(uint32_t now) const {
  return now - this->last_rx_ms_ < AWAKE_FRESH_MS && now - this->awake_since_ms_ >= this->wake_settle_;
}

void KaidiDesk::publish_status_(const char *status) {
  if (this->status_sensor_ == nullptr || this->status_ == status)
    return;
  this->status_ = status;
  this->status_sensor_->publish_state(status);
}

void KaidiDesk::sync_target_() {
  if (this->target_number_ == nullptr || std::isnan(this->height_))
    return;
  float value = std::round(this->height_ * this->units_per_cm_ * 10.0f) / 10.0f;
  if (!this->target_number_->has_state() || this->target_number_->state != value)
    this->target_number_->publish_state(value);
}

void KaidiDesk::move_to(float cm) {
  this->target_ = cm;
  this->moving_up_ = std::isnan(this->height_) || this->height_ < cm;
  if (this->state_ == State::ACTING && this->action_ == Action::MOVE) {
    this->state_since_ms_ = millis();
    return;
  }
  this->begin_(Action::MOVE);
}

void KaidiDesk::apply_wake_pin_() {
  if (this->wake_pin_ != nullptr)
    this->wake_pin_->digital_write(this->keep_awake_ || this->state_ != State::IDLE);
}

void KaidiDesk::set_keep_awake(bool keep_awake) {
  this->keep_awake_ = keep_awake;
  this->keepalive_frames_ = keep_awake ? KEEPALIVE_FRAMES : 0;
  this->apply_wake_pin_();
}

// Holding the wake line alone does not stop the box from sleeping; like the keypad, it needs Idle frames.
void KaidiDesk::keep_alive_(uint32_t now) {
  if (!this->keep_awake_)
    return;
  if (this->keepalive_frames_ == 0 && now - this->last_tx_ms_ >= KEEPALIVE_INTERVAL_MS)
    this->keepalive_frames_ = KEEPALIVE_FRAMES;
  if (this->keepalive_frames_ > 0 && now - this->last_tx_ms_ >= this->frame_interval_) {
    this->send_(COMMAND_IDLE);
    this->keepalive_frames_--;
  }
}

void KaidiDesk::nudge(bool up) { this->begin_(up ? Action::NUDGE_UP : Action::NUDGE_DOWN); }

void KaidiDesk::reset() { this->begin_(Action::RESET); }

void KaidiDesk::stop() {
  if (this->state_ != State::IDLE)
    this->release_();
}

void KaidiTargetNumber::control(float value) {
  this->publish_state(value);
  this->parent_->move_to(value / this->parent_->units_per_cm());
}

void KaidiKeepAwakeSwitch::write_state(bool state) {
  this->parent_->set_keep_awake(state);
  this->publish_state(state);
}

void KaidiButton::press_action() {
  switch (this->action_) {
    case ButtonAction::NUDGE_UP:
      this->parent_->nudge(true);
      break;
    case ButtonAction::NUDGE_DOWN:
      this->parent_->nudge(false);
      break;
    case ButtonAction::STOP:
      this->parent_->stop();
      break;
    case ButtonAction::RESET:
      this->parent_->reset();
      break;
  }
}

}  // namespace kaidi_desk
}  // namespace esphome
