class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.5.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.5.0-bottle-7dd9f9f4dbb9aa20da93cf1242cce91df0cc42824b1a8fe1717e9a4a36034048"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "7dd9f9f4dbb9aa20da93cf1242cce91df0cc42824b1a8fe1717e9a4a36034048"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.5.0/namu_0.5.0_darwin_arm64.tar.gz"
      sha256 "0c34f0b055ce0628799da6a89bd9753805bd84554b7c10230b4afc2b37bd7199"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.5.0/namu_0.5.0_darwin_amd64.tar.gz"
      sha256 "af2237f537c350ee815a85d76e6650348ccfb7e8d67139c5431566b589235011"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.5.0/namu_0.5.0_linux_arm64.tar.gz"
      sha256 "91813d801909a2f6d484909c9de0cf6f3f8d8e1150ec80d4cb47d62b9ad735c4"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.5.0/namu_0.5.0_linux_amd64.tar.gz"
      sha256 "903b5753bf8b3df865cf76928d589c9e4847aab85e47f056e7d7fc23622ef20a"
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
