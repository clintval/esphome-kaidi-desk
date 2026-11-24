#pragma once

#include "esphome/components/button/button.h"
#include "esphome/components/number/number.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"

#include <array>

namespace esphome {
namespace kaidi_desk {

enum Command : uint8_t {
  COMMAND_UP = 0x01,
  COMMAND_DOWN = 0x02,
  COMMAND_IDLE = 0x03,
  COMMAND_RESET = 0x04,
  COMMAND_PRESET_1 = 0x06,
  COMMAND_SAVE_PRESET_1 = 0x0A,
  COMMAND_SAVE_PRESET_2 = 0x0B,
  COMMAND_SAVE_PRESET_3 = 0x0C,
  COMMAND_SAVE_PRESET_4 = 0x17,
};

enum BoxMode : uint8_t {
  BOX_MODE_HEIGHT = 0x00,
  BOX_MODE_REBOUND = 0x04,
  BOX_MODE_RESET_NEEDED = 0x30,
  BOX_MODE_SETTINGS = 0x62,
  BOX_MODE_NONE = 0xFF,
};

enum class Action : uint8_t { NONE, MOVE, NUDGE_UP, NUDGE_DOWN, RESET, PRESET, SAVE_PRESET };

enum class State : uint8_t { IDLE, WAKING, ACTING, RELEASING };

class FrameReader {
 public:
  bool feed(uint8_t byte);
  uint8_t mode() const { return this->mode_; }
  uint16_t value() const { return this->value_; }

 protected:
  uint8_t buffer_[7]{};
  uint8_t length_{0};
  uint8_t mode_{0};
  uint16_t value_{0};
};

// The ESP's own frames can come back on the keypad's side of the line, so each one sent excuses one received.
class EchoFilter {
 public:
  void sent(uint8_t command, uint32_t now);
  bool is_echo(uint8_t command, uint32_t now);

 protected:
  struct Sent {
    uint8_t command{0};
    uint32_t at{0};
  };
  std::array<Sent, 8> sent_{};
  uint8_t next_{0};
};

class KaidiDesk : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_tx_enable_pin(GPIOPin *pin) { this->tx_enable_pin_ = pin; }
  void set_wake_pin(GPIOPin *pin) { this->wake_pin_ = pin; }
  void set_keypad_uart(uart::UARTComponent *uart) { this->keypad_uart_ = uart; }
  void set_height_sensor(sensor::Sensor *sensor) { this->height_sensor_ = sensor; }
  void set_status_sensor(text_sensor::TextSensor *sensor) { this->status_sensor_ = sensor; }
  void set_last_stop_sensor(text_sensor::TextSensor *sensor) { this->last_stop_sensor_ = sensor; }
  void set_keypad_sensor(text_sensor::TextSensor *sensor) { this->keypad_sensor_ = sensor; }
  void set_target_number(number::Number *number, float units_per_cm) {
    this->target_number_ = number;
    this->units_per_cm_ = units_per_cm;
  }
  void set_frame_interval(uint32_t ms) { this->frame_interval_ = ms; }
  void set_wake_settle(uint32_t ms) { this->wake_settle_ = ms; }
  void set_wake_timeout(uint32_t ms) { this->wake_timeout_ = ms; }
  void set_nudge_duration(uint32_t ms) { this->nudge_duration_ = ms; }
  void set_move_timeout(uint32_t ms) { this->move_timeout_ = ms; }
  void set_reset_timeout(uint32_t ms) { this->reset_timeout_ = ms; }
  void set_tolerance(float cm) { this->tolerance_ = cm; }
  void set_coast(float cm) { this->coast_ = cm; }

  void move_to(float cm);
  void nudge(bool up);
  void preset(uint8_t number);
  void save_preset(uint8_t number);
  void reset();
  void stop();
  void set_keep_awake(bool keep_awake);

  float units_per_cm() const { return this->units_per_cm_; }

 protected:
  void read_frames_();
  void handle_frame_(uint8_t mode, uint16_t value);
  void send_(uint8_t command);
  void begin_(Action action);
  void release_(const char *reason);
  void start_motion_();
  const char *motion_fault_(uint32_t now);
  void publish_last_stop_(const char *reason);
  void finish_();
  void step_action_(uint32_t now);
  void publish_status_(const char *status);
  void sync_target_();
  bool box_awake_(uint32_t now) const;
  void keep_alive_(uint32_t now);
  void apply_wake_pin_();
  void read_keypad_(uint32_t now);
  void handle_keypad_frame_(uint8_t command, uint32_t now);
  void end_keypad_press_(uint32_t now);
  bool keypad_awake_(uint32_t now) const;
  void publish_keypad_(uint8_t command);

  GPIOPin *tx_enable_pin_{nullptr};
  GPIOPin *wake_pin_{nullptr};
  uart::UARTComponent *keypad_uart_{nullptr};
  sensor::Sensor *height_sensor_{nullptr};
  text_sensor::TextSensor *status_sensor_{nullptr};
  text_sensor::TextSensor *last_stop_sensor_{nullptr};
  text_sensor::TextSensor *keypad_sensor_{nullptr};
  number::Number *target_number_{nullptr};
  float units_per_cm_{1.0f};

  uint32_t frame_interval_{14};
  uint32_t wake_settle_{1200};
  uint32_t wake_timeout_{4000};
  uint32_t nudge_duration_{900};
  uint32_t move_timeout_{45000};
  uint32_t reset_timeout_{90000};
  float tolerance_{0.4f};
  float coast_{1.3f};
  bool moving_up_{true};
  bool has_moved_{false};
  bool sent_{false};
  float start_height_{NAN};
  float furthest_{NAN};
  uint8_t preset_{0};

  FrameReader box_reader_;

  FrameReader keypad_reader_;
  EchoFilter echoes_;
  bool keypad_seen_{false};
  uint32_t keypad_ms_{0};
  uint8_t keypad_command_{0};
  uint8_t keypad_repeats_{0};
  uint8_t keypad_press_{0};
  uint32_t keypad_press_ms_{0};
  float keypad_press_height_{NAN};
  bool keypad_took_over_{false};
  uint8_t keypad_published_{0xFF};

  float height_{NAN};
  float published_height_{NAN};
  float candidate_{NAN};
  uint32_t height_ms_{0};
  uint32_t last_rx_ms_{0};
  uint32_t awake_since_ms_{0};
  uint8_t box_mode_{BOX_MODE_NONE};
  const char *status_{nullptr};

  State state_{State::IDLE};
  Action action_{Action::NONE};
  float target_{NAN};
  bool reset_seen_{false};
  uint32_t state_since_ms_{0};
  uint32_t last_tx_ms_{0};
  uint8_t release_frames_{0};
  bool keep_awake_{false};
  bool wake_high_{false};
  uint32_t wake_high_since_ms_{0};
  uint8_t keepalive_frames_{0};
  uint32_t motion_ms_{0};

  HighFrequencyLoopRequester high_freq_;
};

class KaidiTargetNumber : public number::Number, public Parented<KaidiDesk> {
 protected:
  void control(float value) override;
};

class KaidiKeepAwakeSwitch : public switch_::Switch, public Parented<KaidiDesk> {
 protected:
  void write_state(bool state) override;
};

enum class ButtonAction : uint8_t {
  NUDGE_UP,
  NUDGE_DOWN,
  STOP,
  RESET,
  PRESET_1,
  PRESET_2,
  PRESET_3,
  PRESET_4,
  SAVE_PRESET_1,
  SAVE_PRESET_2,
  SAVE_PRESET_3,
  SAVE_PRESET_4,
};

class KaidiButton : public button::Button, public Parented<KaidiDesk> {
 public:
  explicit KaidiButton(ButtonAction action) : action_(action) {}

 protected:
  void press_action() override;
  ButtonAction action_;
};

}  // namespace kaidi_desk
}  // namespace esphome
