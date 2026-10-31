class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.4.1"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.4.1-bottle-91eae745f58fbff400261167dd10eb72f9d4b7272d125b9bedcf538fc1dc4a16"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "91eae745f58fbff400261167dd10eb72f9d4b7272d125b9bedcf538fc1dc4a16"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.1/namu_0.4.1_darwin_arm64.tar.gz"
      sha256 "5c857270a1fb8c8bf1af3e7f59f6d4fbbeb0b36be451c3240f7e4bde5879f76d"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.1/namu_0.4.1_darwin_amd64.tar.gz"
      sha256 "c46363fa1bae33a87db5aebb0d34362dc5b369b90c05af6161188ea2356a3fa0"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.1/namu_0.4.1_linux_arm64.tar.gz"
      sha256 "4bc604752fbc7633797133d6b5a511d91f0884c64ba0b09b942b064c4781452a"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.4.1/namu_0.4.1_linux_amd64.tar.gz"
      sha256 "c0052a50f663ba317e5950bd64210ae3b6f83acb891d9ec7f3f9508dfbb54c27"
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
