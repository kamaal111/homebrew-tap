class OpenApiMaker < Formula
  include Language::Python::Virtualenv

  desc "Shiny new formula"
  homepage ""
  url "https://files.pythonhosted.org/packages/94/ef/a0e28d771297e426bbfd53167a39247f319d173ef4b6d2c9b6c8f8e53b4d/open_api_maker_kamaalio-0.0.2.tar.gz"
  sha256 "cf4bb05c66684bcc54e9bc33773cc619f4609a90550b8011c4d04609833b49c3"

  deprecate! date: "2026-10-31", because: "is no longer maintained in this tap"

  depends_on "python3"

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/cd/e5/af35f7ea75cf72f2cd079c95ee16797de7cd71f29ea7c68ae5ce7be1eda0/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"
  end

  def install
    virtualenv_create(libexec, "python3")
    virtualenv_install_with_resources
  end

  test do
    false
  end
end
