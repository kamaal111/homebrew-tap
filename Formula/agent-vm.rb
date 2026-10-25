class AgentVm < Formula
  desc "Persistent development VMs and native coding-agent sessions"
  homepage "https://github.com/kamaal111/agent-vm"
  url "https://github.com/kamaal111/agent-vm/releases/download/v0.1.0/agent-vm_0.1.0_darwin_arm64.tar.gz"
  version "0.1.0"
  sha256 "40d545fbe63a663f017ca54de89af47e6fd287d6b645d1e2dd53afb4b6288a6e"

  depends_on arch: :arm64
  depends_on :macos

  def install
    bin.install "agent-vm"
  end

  def caveats
    <<~EOS
      Run agent-vm config init, then agent-vm doctor.
      Install Tart and prepare guest images and credentials separately.
      See https://github.com/kamaal111/agent-vm#first-setup
    EOS
  end

  test do
    assert_equal "agent-vm version #{version}", shell_output("#{bin}/agent-vm --version").strip
    assert_match "Persistent development VMs", shell_output("#{bin}/agent-vm --help")
  end
end
