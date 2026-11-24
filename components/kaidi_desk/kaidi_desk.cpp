#include "kaidi_desk.h"

#include <algorithm>
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "esphome/core/log.h"

namespace esphome {
namespace kaidi_desk {

static const char *const TAG = "kaidi_desk";

static const uint8_t FRAME_START = 0x68;
static const uint8_t FRAME_ADDRESS = 0x01;
static const uint8_t FRAME_END = 0x16;
static const uint32_t AWAKE_FRESH_MS = 150;
static const uint32_t ASLEEP_AFTER_MS = 2000;
static const uint32_t HEIGHT_STALE_MS = 500;
static const uint32_t WAKE_HOLD_MS = 500;
static const uint8_t RELEASE_IDLE_FRAMES = 3;
static const uint32_t KEEPALIVE_INTERVAL_MS = 10000;
static const uint8_t KEEPALIVE_FRAMES = 3;
static const uint32_t KEEPALIVE_AFTER_MOTION_MS = 3000;
static const uint32_t START_TIMEOUT_MS = 2500;
static const uint32_t STALL_MS = 1500;
static const float MOVED_CM = 0.5f;
static const float MAX_STEP_CM = 2.0f;

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
  LOG_TEXT_SENSOR("  ", "Last Stop", this->last_stop_sensor_);
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
        this->sent_ = false;
        if (this->action_ == Action::MOVE)
          this->moving_up_ = this->height_ < this->target_;
        this->start_motion_();
        this->step_action_(now);
      } else if (now - this->state_since_ms_ > this->wake_timeout_) {
        this->release_("Box did not answer");
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
      if (const char *fault = this->motion_fault_(now)) {
        this->release_(fault);
        return;
      }
      float remaining = this->moving_up_ ? this->target_ - this->height_ : this->height_ - this->target_;
      bool close = std::fabs(this->height_ - this->target_) <= this->tolerance_;
      if (close || remaining <= this->coast_) {
        if (this->sent_)
          this->release_("Reached target");
        else
          this->release_(close ? "Already at target" : "Target too close to move");
        return;
      }
      this->send_(this->moving_up_ ? COMMAND_UP : COMMAND_DOWN);
      this->sent_ = true;
      return;
    }
    case Action::PRESET: {
      char reason[40];
      bool done = this->has_moved_ && now - this->motion_ms_ > STALL_MS;
      bool unmoved = !this->has_moved_ && elapsed > START_TIMEOUT_MS && this->box_mode_ == BOX_MODE_HEIGHT;
      if (done || unmoved) {
        snprintf(reason, sizeof(reason), done ? "Reached preset %u" : "Already at preset %u, or not saved",
                 this->preset_);
        this->release_(reason);
        return;
      }
      if (const char *fault = this->motion_fault_(now)) {
        this->release_(fault);
        return;
      }
      this->send_(COMMAND_PRESET_1 + this->preset_ - 1);
      return;
    }
    case Action::NUDGE_UP:
    case Action::NUDGE_DOWN:
      if (elapsed >= this->nudge_duration_) {
        this->release_("Nudge finished");
        return;
      }
      this->send_(this->action_ == Action::NUDGE_UP ? COMMAND_UP : COMMAND_DOWN);
      return;
    case Action::RESET:
      if (this->box_mode_ == BOX_MODE_RESET_NEEDED || this->box_mode_ == BOX_MODE_REBOUND)
        this->reset_seen_ = true;
      if (this->reset_seen_ && this->box_mode_ == BOX_MODE_HEIGHT) {
        this->release_("Reset finished");
        return;
      }
      if (!this->reset_seen_ && elapsed > 5000) {
        this->release_("Reset never started");
        return;
      }
      if (elapsed > this->reset_timeout_) {
        this->release_("Reset timed out");
        return;
      }
      this->send_(COMMAND_RESET);
      return;
    default:
      this->release_("Stopped");
      return;
  }
}

void KaidiDesk::start_motion_() {
  this->start_height_ = this->height_;
  this->furthest_ = this->height_;
  this->has_moved_ = false;
}

const char *KaidiDesk::motion_fault_(uint32_t now) {
  if (this->box_mode_ == BOX_MODE_RESET_NEEDED || this->box_mode_ == BOX_MODE_REBOUND)
    return "Reset needed";
  if (std::isnan(this->height_) || now - this->height_ms_ > HEIGHT_STALE_MS)
    return "Lost the height";
  uint32_t elapsed = now - this->state_since_ms_;
  if (elapsed > this->move_timeout_)
    return "Timed out";
  if (!this->has_moved_)
    return elapsed > START_TIMEOUT_MS ? "Did not move" : nullptr;
  if ((this->moving_up_ ? this->furthest_ - this->height_ : this->height_ - this->furthest_) >= MOVED_CM)
    return "Reversed by an obstruction or the keypad";
  if (now - this->motion_ms_ > STALL_MS)
    return "Stopped short at a limit or obstruction";
  return nullptr;
}

void KaidiDesk::read_frames_() {
  uint8_t byte;
  while (this->available() > 0 && this->read_byte(&byte)) {
    if (this->buffer_len_ == 0 && byte != FRAME_START)
      continue;
    this->buffer_[this->buffer_len_++] = byte;
    if (this->buffer_len_ < sizeof(this->buffer_))
      continue;
    const uint8_t *p = this->buffer_;
    uint8_t checksum = p[1] + p[2] + p[3] + p[4];
    if (p[1] == FRAME_ADDRESS && p[5] == checksum && p[6] == FRAME_END) {
      this->buffer_len_ = 0;
      this->handle_frame_(p[2], (p[3] << 8) | p[4]);
      continue;
    }
    ESP_LOGV(TAG, "Dropped malformed frame");
    uint8_t next = 1;
    while (next < sizeof(this->buffer_) && this->buffer_[next] != FRAME_START)
      next++;
    this->buffer_len_ = sizeof(this->buffer_) - next;
    memmove(this->buffer_, this->buffer_ + next, this->buffer_len_);
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
      case BOX_MODE_SETTINGS:
        this->publish_status_("Keypad Settings");
        break;
      default:
        ESP_LOGD(TAG, "Unknown box mode 0x%02X", mode);
        this->publish_status_("Unknown");
        break;
    }
  }
  if (mode != BOX_MODE_HEIGHT)
    return;

  float height = value / 10.0f;
  float previous = this->candidate_;
  this->candidate_ = height;
  if (!std::isnan(this->height_) && std::fabs(height - this->height_) > MAX_STEP_CM &&
      !(std::fabs(height - previous) <= MAX_STEP_CM))
    return;
  if (height != this->height_)
    this->motion_ms_ = now;
  this->height_ = height;
  this->height_ms_ = now;
  if (this->state_ == State::ACTING) {
    float climbed = height - this->start_height_;
    if (!this->has_moved_) {
      if (this->action_ == Action::PRESET && std::fabs(climbed) >= MOVED_CM)
        this->moving_up_ = climbed > 0;
      this->has_moved_ = (this->moving_up_ ? climbed : -climbed) >= MOVED_CM;
      this->furthest_ = height;
    }
    this->furthest_ = this->moving_up_ ? std::max(this->furthest_, height) : std::min(this->furthest_, height);
  }
  if (this->height_sensor_ != nullptr && this->height_ != this->published_height_) {
    this->published_height_ = this->height_;
    this->height_sensor_->publish_state(this->height_);
  }
  if (this->state_ == State::IDLE)
    this->sync_target_();
}

void KaidiDesk::send_(uint8_t command) {
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
  if (this->action_ == Action::RESET && this->state_ != State::IDLE) {
    ESP_LOGW(TAG, "Ignored while the box resets; only Stop can end a reset early");
    return;
  }
  this->action_ = action;
  this->state_ = State::WAKING;
  this->state_since_ms_ = millis();
  this->apply_wake_pin_();
  this->high_freq_.start();
}

void KaidiDesk::release_(const char *reason) {
  this->publish_last_stop_(reason);
  this->state_ = State::RELEASING;
  this->release_frames_ = RELEASE_IDLE_FRAMES;
}

void KaidiDesk::abort_for_keypad_() {
  this->publish_last_stop_("Keypad took over");
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
  return now - this->last_rx_ms_ < AWAKE_FRESH_MS && now - this->awake_since_ms_ >= this->wake_settle_ &&
         now - this->wake_high_since_ms_ >= this->wake_settle_;
}

void KaidiDesk::publish_status_(const char *status) {
  if (this->status_sensor_ == nullptr || this->status_ == status)
    return;
  this->status_ = status;
  this->status_sensor_->publish_state(status);
}

void KaidiDesk::publish_last_stop_(const char *reason) {
  ESP_LOGI(TAG, "Stopped at %.1f cm: %s", this->height_, reason);
  if (this->last_stop_sensor_ != nullptr)
    this->last_stop_sensor_->publish_state(reason);
}

void KaidiDesk::sync_target_() {
  if (this->target_number_ == nullptr || std::isnan(this->height_))
    return;
  float value = std::round(this->height_ * this->units_per_cm_ * 10.0f) / 10.0f;
  if (!this->target_number_->has_state() || this->target_number_->state != value)
    this->target_number_->publish_state(value);
}

void KaidiDesk::move_to(float cm) {
  if (this->action_ == Action::RESET && this->state_ != State::IDLE) {
    ESP_LOGW(TAG, "Ignored while the box resets; only Stop can end a reset early");
    this->sync_target_();
    return;
  }
  this->target_ = cm;
  this->moving_up_ = std::isnan(this->height_) || this->height_ < cm;
  if (this->state_ == State::ACTING && this->action_ == Action::MOVE) {
    this->state_since_ms_ = millis();
    this->start_motion_();
    return;
  }
  this->begin_(Action::MOVE);
}

void KaidiDesk::preset(uint8_t number) {
  if (this->action_ != Action::RESET)
    this->preset_ = number;
  this->begin_(Action::PRESET);
}

void KaidiDesk::apply_wake_pin_() {
  if (this->wake_pin_ == nullptr)
    return;
  bool high = this->keep_awake_ || this->state_ != State::IDLE;
  if (high && !this->wake_high_)
    this->wake_high_since_ms_ = millis();
  this->wake_high_ = high;
  this->wake_pin_->digital_write(high);
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
  // The box is awake while it moves, and a burst then would cut into the keypad's own frames.
  if (now - this->motion_ms_ < KEEPALIVE_AFTER_MOTION_MS) {
    this->keepalive_frames_ = 0;
    return;
  }
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
  if (this->state_ == State::WAKING || this->state_ == State::ACTING)
    this->release_("Stopped");
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
    default:
      this->parent_->preset(static_cast<uint8_t>(this->action_) - static_cast<uint8_t>(ButtonAction::PRESET_1) + 1);
      break;
  }
}

}  // namespace kaidi_desk
}  // namespace esphome
