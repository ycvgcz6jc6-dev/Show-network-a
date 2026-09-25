#include <la/avdecc/controller/avdeccController.hpp>
#include <la/avdecc/utils.hpp>

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <string>
#include <thread>

namespace {
constexpr auto VendorID = std::uint32_t{0x001B92};
constexpr auto DeviceID = std::uint32_t{0x80};
constexpr auto ModelID = std::uint32_t{0x00000001};
std::atomic_bool g_run{true};

void onSignal(int) { g_run.store(false); }

class Observer final : public la::avdecc::controller::Controller::DefaultedObserver {
public:
  void onEntityOnline(la::avdecc::controller::Controller const*, la::avdecc::controller::ControlledEntity const* entity) noexcept override {
    std::cerr << "[avdecc] online " << la::avdecc::utils::toHexString(entity->getEntity().getEntityID(), true) << "\n";
  }
  void onEntityOffline(la::avdecc::controller::Controller const*, la::avdecc::controller::ControlledEntity const* entity) noexcept override {
    std::cerr << "[avdecc] offline " << la::avdecc::utils::toHexString(entity->getEntity().getEntityID(), true) << "\n";
  }
  void onTransportError(la::avdecc::controller::Controller const*, la::avdecc::controller::InterfaceType const type) noexcept override {
    std::cerr << "[avdecc] transport error on " << (type == la::avdecc::controller::InterfaceType::Primary ? "primary" : "secondary") << " interface\n";
  }
};

void usage(char const* argv0) {
  std::cerr << "Usage: " << argv0 << " --interface <id> --output <file> [--interval <seconds>]\n";
}
}

int main(int argc, char** argv) {
  std::string interfaceID;
  std::string output = "/data/avdecc-network.json";
  double interval = 2.0;
  for (int i = 1; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "--interface" && i + 1 < argc) interfaceID = argv[++i];
    else if (arg == "--output" && i + 1 < argc) output = argv[++i];
    else if (arg == "--interval" && i + 1 < argc) interval = std::stod(argv[++i]);
    else if (arg == "--help" || arg == "-h") { usage(argv[0]); return 0; }
    else { usage(argv[0]); return 2; }
  }
  if (interfaceID.empty()) { usage(argv[0]); return 2; }
  if (interval < 0.25) interval = 0.25;

  std::signal(SIGINT, onSignal);
  std::signal(SIGTERM, onSignal);

  try {
    auto controller = la::avdecc::controller::Controller::create(
      la::avdecc::protocol::ProtocolInterface::Type::PCap,
      interfaceID,
      0x0001,
      la::avdecc::entity::model::makeEntityModelID(VendorID, DeviceID, ModelID),
      "en", nullptr, std::nullopt, nullptr);
    Observer observer;
    controller->registerObserver(&observer);
    controller->enableEntityAdvertising(10);

    auto const flags = la::avdecc::entity::model::jsonSerializer::Flags{
      la::avdecc::entity::model::jsonSerializer::Flag::IgnoreAEMSanityChecks,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessADP,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessCompatibility,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessDiagnostics,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessDynamicModel,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessMilan,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessState,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessStaticModel,
      la::avdecc::entity::model::jsonSerializer::Flag::ProcessStatistics};

    auto target = std::filesystem::path(output);
    if (target.has_parent_path()) std::filesystem::create_directories(target.parent_path());
    auto temp = target; temp += ".tmp";
    while (g_run.load()) {
      auto const [error, message] = controller->serializeAllControlledEntitiesAsJson(
        temp.string(), flags, "Show Network LA_avdecc helper", false);
      if (!!error) {
        std::cerr << "[avdecc] JSON dump failed: " << message << "\n";
      } else {
        std::error_code ec;
        std::filesystem::rename(temp, target, ec);
        if (ec) {
          std::filesystem::remove(target, ec);
          ec.clear();
          std::filesystem::rename(temp, target, ec);
        }
        if (ec) std::cerr << "[avdecc] atomic publish failed: " << ec.message() << "\n";
      }
      std::this_thread::sleep_for(std::chrono::duration<double>(interval));
    }
    controller->unregisterObserver(&observer);
  } catch (std::exception const& e) {
    std::cerr << "[avdecc] fatal: " << e.what() << "\n";
    return 1;
  }
  return 0;
}
