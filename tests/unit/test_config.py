from msm_core.config import MSMConfig

def test_default_config():
    config = MSMConfig()
    assert config.default_java_memory == "2G"
    assert config.web_port == 5000
