from click.testing import CliRunner
from mock_server.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Mock Server Control Panel" in result.output


def test_cli_status():
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "MOCK SERVER CONTROL PANEL" in result.output
