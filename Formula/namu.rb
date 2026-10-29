class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.1.0"

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.1.0/namu_0.1.0_darwin_arm64.tar.gz"
      sha256 "e93ebb352f0fd83bdef52452299d8b645beff0ea9992afbca8d3be78f4e70404"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.1.0/namu_0.1.0_darwin_amd64.tar.gz"
      sha256 "b1965210154afeea8948b41a4205054a9cdc7f5e44fc78abc3e5684e12619d4f"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.1.0/namu_0.1.0_linux_arm64.tar.gz"
      sha256 "76b1e68da3e9a92dabee5369ce499fe5b108c4ea68854d303b6abc5f8144f5b2"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.1.0/namu_0.1.0_linux_amd64.tar.gz"
      sha256 "a9904060327d409c686513484bfc46924358075d7b1fbd13f5b916db9fb28427"
    end
  end

  def install
    bin.install "namu"
  end

  test do
    assert_equal "namu version #{version}", shell_output("#{bin}/namu --version").strip
    assert_match "Git worktrees", shell_output("#{bin}/namu --help")

    ENV["GIT_CONFIG_GLOBAL"] = File::NULL
    ENV["GIT_CONFIG_NOSYSTEM"] = "1"
    system "git", "init", "--initial-branch=main"
    system "git", "-c", "user.name=Homebrew Test", "-c", "user.email=test@example.com",
           "commit", "--allow-empty", "-m", "Initial commit"

    checkout = testpath.realpath/".agents/worktrees/feature/homebrew"
    assert_equal checkout.to_s, shell_output("#{bin}/namu create feature/homebrew --base main").strip
    assert_path_exists checkout/".git"
    assert_equal checkout.to_s, shell_output("#{bin}/namu open feature/homebrew").strip
    assert_match "feature/homebrew", shell_output("#{bin}/namu list")

    system bin/"namu", "delete", "feature/homebrew"
    refute_path_exists checkout
    assert_match "feature/homebrew", shell_output("git branch --list feature/homebrew")
  end
end
