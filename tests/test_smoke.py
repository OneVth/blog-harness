def test_package_imports():
    """src 레이아웃이 설치되어 패키지가 import되는지 검증한다."""
    import blog_harness

    assert blog_harness.__doc__
