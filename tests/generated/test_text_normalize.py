def test_text_normalize(tmp_path):
    p = tmp_path / 'a.txt'
    p.write_text(' a  \n b ')
    from agentmx.skills.generated.text_normalize import TextNormalizeSkill
    s = TextNormalizeSkill()
    out = s.run(str(p))
    import pathlib
    assert pathlib.Path(out).read_text() == 'a\nb\n'
