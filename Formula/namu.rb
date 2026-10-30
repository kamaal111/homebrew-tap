class Namu < Formula
  desc "Create, open, list and delete Git worktrees"
  homepage "https://github.com/kamaal111/namu"
  version "0.2.0"

  bottle do
    root_url "https://github.com/kamaal111/homebrew-tap/releases/download/namu-v0.2.0-bottle-e2da498a785c705ca5691e7a5d2e1567a14258f485b2bb4808ec2ce4dd495076"
    sha256 cellar: :any_skip_relocation, arm64_sequoia: "e2da498a785c705ca5691e7a5d2e1567a14258f485b2bb4808ec2ce4dd495076"
  end

  uses_from_macos "git"

  on_macos do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.2.0/namu_0.2.0_darwin_arm64.tar.gz"
      sha256 "8a3b684a79f4ba52b351fd360ddc55fc7a9afd25751e7b571ced92cdb81138aa"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.2.0/namu_0.2.0_darwin_amd64.tar.gz"
      sha256 "32323f72ea6035bbe8ca6cb70fb17b2dc28fce52eca1e68c96bc523e4ac7045e"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/kamaal111/namu/releases/download/v0.2.0/namu_0.2.0_linux_arm64.tar.gz"
      sha256 "da420e09298da8708c252c25f307913e07766e9c9d74810ad3062d71f036a4fd"
    end
    on_intel do
      url "https://github.com/kamaal111/namu/releases/download/v0.2.0/namu_0.2.0_linux_amd64.tar.gz"
      sha256 "fa614bffb74cb311a4aa3fb5d0c0200bd0fc2beb28b0b7c30fc2460c9fb32a31"
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
