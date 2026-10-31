class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.3.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.3.0-bottle-2d774cf3d3c02248095d31908ab933afa22a1b538e9434fd6e09e00cf88f7deb"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "2d774cf3d3c02248095d31908ab933afa22a1b538e9434fd6e09e00cf88f7deb"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.3.0/namu_0.3.0_darwin_arm64.tar.gz"
      sha256 "5d3c796e7320d3ec5be46292eafe8115680b2c4925e922382c4c3f0ccbf9f7f7"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.3.0/namu_0.3.0_darwin_amd64.tar.gz"
      sha256 "0abf121f759cfed1c2b88872acb58d77d3986756a235d1161225576f4a1aa05d"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.3.0/namu_0.3.0_linux_arm64.tar.gz"
      sha256 "a3e99f8d6d910f124160c05ba7aa9088c021e9d16e4f5d14c5ce092e7c590889"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.3.0/namu_0.3.0_linux_amd64.tar.gz"
      sha256 "7da1f18ce6e71ff8c3e723c5b36611953dec7dcd0763c4a53dd98cd5f9fe8813"
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
