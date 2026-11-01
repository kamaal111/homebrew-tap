class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.6.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.6.0-bottle-ec5ab2952d47dd68452c70fc7011ce7f4eb776f3b020567abaa393d40cd679e6"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "ec5ab2952d47dd68452c70fc7011ce7f4eb776f3b020567abaa393d40cd679e6"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.6.0/namu_0.6.0_darwin_arm64.tar.gz"
      sha256 "b6818dc298d225c5ed41dd10d159ee686909167e6a464784cbd0ecd23ca4b9f1"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.6.0/namu_0.6.0_darwin_amd64.tar.gz"
      sha256 "4648862f1097dc1fb7a11d6e8853f2bc999874adfd361807c737a1e642f6efcd"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.6.0/namu_0.6.0_linux_arm64.tar.gz"
      sha256 "26b6a27e828b5bdf912563e7ef28ade1ae5257b2bdc98ed032bfc63a682ce79f"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.6.0/namu_0.6.0_linux_amd64.tar.gz"
      sha256 "607a33108059f0d944a86896479dea8e3591dc021aecd87774b4d6ac95c5aada"
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
