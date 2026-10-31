class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.4.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.4.0-bottle-ad2a236e67122cb92cb203b8e0fd0b4bef8b4122c10cf1d85e694f6b16fef2bb"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "ad2a236e67122cb92cb203b8e0fd0b4bef8b4122c10cf1d85e694f6b16fef2bb"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.0/namu_0.4.0_darwin_arm64.tar.gz"
      sha256 "739db4b53f052fca8fb38af758044c71461fad77ec8e68621d021006bfb6e18c"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.0/namu_0.4.0_darwin_amd64.tar.gz"
      sha256 "3e6345968c53a6bdbfe525ff467305bf558d069ecde59164c3eab98137b58aec"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.0/namu_0.4.0_linux_arm64.tar.gz"
      sha256 "117bf66880887b2d6b4d4cc93d2f346cf843574ae5ec84c5b05e6531561578bf"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.0/namu_0.4.0_linux_amd64.tar.gz"
      sha256 "1e7097741f435b6a97256fdf46bfec2a3cfd0b84aaa7158c65b7787a25c99f27"
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
    created = shell_output("#{bin}/namu create feature/homebrew --base main").strip
    assert_equal checkout, Pathname.new(created).expand_path.realpath
    assert_path_exists checkout/".git"
    opened = shell_output("#{bin}/namu open feature/homebrew").strip
    assert_equal checkout, Pathname.new(opened).expand_path.realpath
    assert_match "feature/homebrew", shell_output("#{bin}/namu list")

    system bin/"namu", "delete", "feature/homebrew"
    refute_path_exists checkout
    assert_match "feature/homebrew", shell_output("git branch --list feature/homebrew")
  end
end
