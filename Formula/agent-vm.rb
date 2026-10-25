class AgentVm < Formula
  desc "Persistent development VMs and native coding-agent sessions"
  homepage "https://github.com/kamaal111/agent-vm"
  url "https://github.com/kamaal111/agent-vm/releases/download/v0.2.0/agent-vm_0.2.0_darwin_arm64.tar.gz"
  version "0.2.0"
  sha256 "e447dc1a0c51de61e8609272a526053eceab7ac87a24b868ebae8c14d4159629"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/agent-vm-v0.2.0-bottle-d7908f280417d56fe2a4ea9bfec2bc0ed8fbffd9d5fd33bc8d568c722943f363"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "d7908f280417d56fe2a4ea9bfec2bc0ed8fbffd9d5fd33bc8d568c722943f363"
  end

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
