class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.7.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.7.0-bottle-a560e59336025bc343acc4e004d054f643989e4695b1b4bcf8f6954ef37a826e"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "a560e59336025bc343acc4e004d054f643989e4695b1b4bcf8f6954ef37a826e"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.7.0/namu_0.7.0_darwin_arm64.tar.gz"
      sha256 "632fe6a8efe11be7c7dbf83812eae6162153bfff65766780f59b0edb5cbb487a"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.7.0/namu_0.7.0_darwin_amd64.tar.gz"
      sha256 "74348f53c57b2a4d50430d10ef0994f1cf3e5bbc736b77fb63af119ad7dc86a9"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.7.0/namu_0.7.0_linux_arm64.tar.gz"
      sha256 "73d9b863f7b67f7ba4d5f60c0796c7a9edc43fabf63114e7f16918c3e77f5d21"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.7.0/namu_0.7.0_linux_amd64.tar.gz"
      sha256 "a6a9f91c5ff6221cea60c5a176d9b46ffbf20dce715a22c54498dbbc762d4ba6"
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
