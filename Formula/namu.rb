class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.8.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.8.0-bottle-62ae068d085759a029b188e6abf9d2bc59ccdf43e2f6249c0a9c07524a1073c9"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "62ae068d085759a029b188e6abf9d2bc59ccdf43e2f6249c0a9c07524a1073c9"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.8.0/namu_0.8.0_darwin_arm64.tar.gz"
      sha256 "206c3bb01c7bb57ceeb99f28b840a05890298ff7e283e0b9eea6555575a63388"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.8.0/namu_0.8.0_darwin_amd64.tar.gz"
      sha256 "e9ffe0ec4e6af495f6cfb21346783989e6351d7d13d1e63605f13f9e01df25f3"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.8.0/namu_0.8.0_linux_arm64.tar.gz"
      sha256 "32f33baf95799daca6622110dfd0780824e34c1ac02c352372c87cf6e5b82093"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.8.0/namu_0.8.0_linux_amd64.tar.gz"
      sha256 "f637739b92c6ecdddc8fc1e52b8a193ac98a9ab86535dab37d53c87a0aa3f780"
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
