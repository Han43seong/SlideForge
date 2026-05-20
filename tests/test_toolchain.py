from slideforge.toolchain import default_toolchain


def test_default_toolchain_is_fixed_to_two_production_routes():
    toolchain = default_toolchain()

    assert toolchain.asset_forge == "ComfyUI"
    assert toolchain.primary_composer == "codex-guizang-html"
    assert toolchain.pptx_delivery == "codex-presentation-pptx"
