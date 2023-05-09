"""Main unit test module."""
import json
import os
from textwrap import dedent
from unittest import mock

from lib_logrotate import LogrotateHelper

import pytest


class TestLogrotateHelper:
    """Main test class."""

    def test_pytest(self):
        """Simple pytest."""
        assert True

    def test_daily_retention_count(self, logrotate):
        """Test daily retention count."""
        logrotate.retention = 90
        contents = "/var/log/apt/history.log {\n  rotate 123\n  daily\n}"
        count = logrotate.calculate_count(contents, logrotate.retention)
        assert count == 90

    def test_weekly_retention_count(self, logrotate):
        """Test weekly retention count."""
        logrotate.retention = 21
        contents = "/var/log/apt/history.log {\n  rotate 123\n  weekly\n}"
        count = logrotate.calculate_count(contents, logrotate.retention)
        assert count == 3

    def test_monthly_retention_count(self, logrotate):
        """Test monthly retention count."""
        logrotate.retention = 60
        contents = "/var/log/apt/history.log {\n  rotate 123\n  monthly\n}"
        count = logrotate.calculate_count(contents, logrotate.retention)
        assert count == 2

    def test_yearly_retention_count(self, logrotate):
        """Test yearly retention count."""
        logrotate.retention = 180
        contents = "/var/log/apt/history.log {\n  rotate 123\n  yearly\n}"
        count = logrotate.calculate_count(contents, logrotate.retention)
        assert count == 1

    def test_modify_content(self, logrotate):
        """Test the modify_content method."""
        file_path = "/var/log/myrandom"
        logrotate.retention = 42
        logrotate.override = []
        logrotate.override_files = []
        contents = (
            "/log/some.log {\n  rotate 123\n  daily\n}\n"
            "/log/other.log {\n  rotate 456\n  weekly\n}"
        )
        mod_contents = logrotate.modify_content(logrotate, contents, file_path)
        expected_contents = (
            "\n/log/some.log {\n  rotate 42\n  daily\n}\n\n"
            "/log/other.log {\n  rotate 6\n  weekly\n}\n"
        )
        assert mod_contents == expected_contents

    def test_empty_line_additions(self, logrotate):
        """Test the modify_content method."""
        file_path = "/etc/logrotate.d/apt"
        logrotate.retention = 42
        logrotate.override = []
        logrotate.override_files = []
        contents = (
            "\n\n\n\n\n/var/log/apt/history.log {\n  rotate 123\n  daily\n}\n\n"
            "\n\n\n/var/log/apt/term.log {\n  rotate 456\n  weekly\n}\n"
        )
        mod_contents = logrotate.modify_content(logrotate, contents, file_path)
        expected_contents = (
            "\n/var/log/apt/history.log {\n  rotate 42\n  daily\n}\n\n"
            "/var/log/apt/term.log {\n  rotate 6\n  weekly\n}\n"
        )
        assert mod_contents == expected_contents

    def test_modify_content_override(self, logrotate):
        """Test the modify_content method."""
        file_path = "/etc/logrotate.d/apt"
        logrotate.retention = 42
        logrotate.override = []
        logrotate.override_files = []
        contents = (
            "/var/log/apt/history.log {\n  rotate 123\n  daily\n}\n"
            "/var/log/apt/term.log {\n  rotate 456\n  weekly\n}"
        )
        mod_contents = logrotate.modify_content(logrotate, contents, file_path)
        expected_contents = (
            "\n/var/log/apt/history.log {\n  rotate 42\n  daily\n}\n\n"
            "/var/log/apt/term.log {\n  rotate 6\n  weekly\n}\n"
        )
        assert mod_contents == expected_contents

    def test_modify_content_with_postrotate_sub(self, logrotate):
        """Test modify_content substitutes if postrotate exists."""
        file_path = "/etc/logrotate.d/apt"
        logrotate.retention = 42
        logrotate.override = []
        logrotate.override_files = []
        contents = (
            "/var/log/apt/history.log {\n"
            "  postrotate\n"
            "    /bin/script\n"
            "  endscript\n"
            "  rotate 123\n"
            "  daily\n}\n"
        )
        mod_contents = logrotate.modify_content(logrotate, contents, file_path)
        expected_contents = (
            "\n/var/log/apt/history.log {\n"
            "  postrotate\n"
            "    /bin/script\n"
            "  endscript\n"
            "  rotate 42\n"
            "  daily\n}\n"
        )
        assert mod_contents == expected_contents

    def test_modify_content_with_postrotate_append(self, logrotate):
        """Test the modify_content appends if postrotate exists."""
        file_path = "/etc/logrotate.d/apt"
        logrotate.retention = 42
        logrotate.override = []
        logrotate.override_files = []
        # fmt: off
        contents = (
            "/var/log/apt/history.log {\n"
            "  postrotate\n"
            "    /bin/script\n"
            "  endscript\n}\n"
        )
        # fmt: on
        mod_contents = logrotate.modify_content(logrotate, contents, file_path)
        expected_contents = (
            "\n/var/log/apt/history.log {\n"
            "  postrotate\n"
            "    /bin/script\n"
            "  endscript\n"
            "    rotate 42\n}\n"
        )
        assert mod_contents == expected_contents

    @pytest.mark.parametrize("header_count", [0, 1, 2, 10])
    def test_modify_header(self, logrotate, header_count):
        """Test the modify_header method works and is idempotent."""
        header = "# Configuration file maintained by Juju. Local changes may be overwritten\n"  # noqa
        content_body = (
            "\n/log/some.log {\n  rotate 42\n  daily\n}\n\n"
            "/log/other.log {\n  rotate 6\n  weekly\n}\n"
        )
        content = (header * header_count) + content_body
        expected_content = (
            header + "/log/some.log {\n  rotate 42\n  daily\n}\n"
            "/log/other.log {\n  rotate 6\n  weekly\n}\n"
        )
        modified_content = logrotate.modify_header(logrotate, content)
        assert modified_content == expected_content

    @pytest.mark.parametrize(
        "test_override,input_contents,expected_contents",
        [
            (
                "[ {} ]",
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 12\n  daily\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}\n",
            ),
            (
                '[ {"path": "/etc/logrotate.d/apt", "rotate": 5} ]',
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 5\n  daily\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 5\n  daily\n}\n",
            ),
            (
                '[ {"path": "/etc/logrotate.d/apt", "interval": "monthly"} ]',
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 12\n  monthly\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  monthly\n}\n",
            ),
            (
                '[{"path":"/etc/logrotate.d/apt","rotate":5, "interval":"monthly"}]',
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 5\n  monthly\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 5\n  monthly\n}\n",
            ),
            (
                '[{"path":"/etc/logrotate.d/apt","rotate":5, "size":"100"}]',
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 5\n  size 100\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 5\n  size 100\n}\n",
            ),
            (
                '[{"path":"/etc/logrotate.d/apt","rotate":5, "interval":"monthly",'
                + '"size":"1G"}]',
                "/var/log/apt/history.log {\n  rotate 12\n  daily\n}"
                + "\n/var/log/apt/term.log {\n  rotate 12\n  daily\n}",
                "\n/var/log/apt/history.log {\n  rotate 5\n  size 1G\n}\n"
                + "\n/var/log/apt/term.log {\n  rotate 5\n  size 1G\n}\n",
            ),
        ],
    )
    def test_override_config_option(
        self, test_override, input_contents, expected_contents
    ):
        """Test override config option."""
        with mock.patch("lib_logrotate.hookenv.config") as mock_config:
            mock_config.return_value = "[]"
            file_path = "/etc/logrotate.d/apt"
            logrotate_helper = LogrotateHelper()
            logrotate_helper.retention = 12
            logrotate_helper.override = json.loads(test_override)
            logrotate_helper.override_files = logrotate_helper.get_override_files()
            mod_contents = logrotate_helper.modify_content(input_contents, file_path)
            assert mod_contents == expected_contents


class TestCronHelper:
    """Main cron test class."""

    def test_cron_daily_schedule_unset(self, cron):
        """Test the validation of unset update-cron-daily-schedule config value."""
        cron_config = cron()
        cron_config.cronjob_enabled = True
        cron_config.cronjob_frequency = 1
        cron_config.cron_daily_schedule = "unset"

        assert cron_config.validate_cron_conf()

    @pytest.mark.parametrize(
        ("cron_schedule, exp_pattern"),
        [
            ("random,06:00,07:50", "00~50 06~07"),
            ("random,06:00,07:00", "00~00 06~07"),
            ("random,07:00,07:45", "00~45 07~07"),
            ("set,08:00", "00 08"),
            ("unset", "25 6"),
        ],
    )
    def test_cron_daily_schedule(self, cron, cron_schedule, exp_pattern, mocker):
        """Test the validate and update random cron.daily schedule."""
        cron_config = cron()
        cron_config.cronjob_enabled = True
        cron_config.cronjob_frequency = 1
        cron_config.cron_daily_schedule = cron_schedule

        mock_method = mocker.Mock()
        mocker.patch.object(cron, "write_to_crontab", new=mock_method)

        updated_cron_daily = cron_config.update_cron_daily_schedule()

        assert cron_config.validate_cron_conf()
        assert updated_cron_daily.split("\t")[0] == exp_pattern
        mock_method.assert_called_once_with(exp_pattern)

    @pytest.mark.parametrize("cron_daily_timestamp", ["00 08", "25 6", "00~50 06~07"])
    def test_write_to_crontab(self, cron, cron_daily_timestamp, mocker):
        """Test function that writes updated data to /etc/crontab."""
        cron_config = cron()
        mock_open = mocker.patch("lib_cron.open")
        mock_handle = mock_open.return_value.__enter__.return_value
        default_crontab_contents = dedent(
            """
            # some comment
            17 *\t* * * root cd / && run-parts --report /etc/cron.hourly
            25 6\t* * root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.daily )
            47 6\t* * 7 root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.weekly )
            52 6\t1 * * root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.monthly )
            #
            """  # noqa
        )
        updated_crontab_contents = dedent(
            f"""
            # some comment
            17 *\t* * * root cd / && run-parts --report /etc/cron.hourly
            {cron_daily_timestamp}\t* * root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.daily )
            47 6\t* * 7 root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.weekly )
            52 6\t1 * * root test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.monthly )
            #
            """  # noqa
        )
        mock_handle.read.return_value = default_crontab_contents
        cron_config.write_to_crontab(cron_daily_timestamp)

        mock_open.assert_any_call("/etc/crontab", "r")
        mock_open.assert_any_call("/etc/crontab", "w")
        mock_handle.write.assert_called_with(updated_crontab_contents)

    @pytest.mark.parametrize(
        ("cron_schedule"),
        [
            ("random,07:00,06:50"),
            ("random,07:50,07:00"),
            ("random,59:50,07:00"),
            ("random,07:00,39:00"),
            ("set,28:00"),
            ("set,02:80"),
        ],
    )
    def test_invalid_cron_daily_schedule(self, cron, cron_schedule):
        """Test the validate and update random cron.daily schedule."""
        cron_config = cron()
        cron_config.cronjob_enabled = True
        cron_config.cronjob_frequency = 1
        cron_config.cron_daily_schedule = cron_schedule

        with pytest.raises(cron_config.InvalidCronConfig) as err:
            cron_config.validate_cron_conf()

        assert err.type == cron_config.InvalidCronConfig

    def test_install_cronjob(self, cron, mock_local_unit, mocker):
        """Test install cronjob method."""
        mock_charm_dir = "/mock/unit-logrotated-0/charm"
        mock_exists = mocker.patch("lib_cron.os.path.exists", return_value=True)
        mock_remove = mocker.patch("lib_cron.os.remove")
        mock_chmod = mocker.patch("lib_cron.os.chmod")
        mocker.patch(
            "lib_cron.os.path.realpath",
            return_value=os.path.join(mock_charm_dir, "lib/lib_cron.py"),
        )
        mocker.patch("lib_cron.os.getcwd", return_value=mock_charm_dir)
        mock_open = mocker.patch("lib_cron.open")
        mock_handle = mock_open.return_value.__enter__.return_value
        expected_files_to_be_removed = [
            "/etc/cron.hourly/charm-logrotate",
            "/etc/cron.daily/charm-logrotate",
            "/etc/cron.weekly/charm-logrotate",
            "/etc/cron.monthly/charm-logrotate",
        ]

        cron_config = cron()
        cron_config.cronjob_enabled = True
        cron_config.cronjob_frequency = 2
        cron_config.install_cronjob()

        mock_exists.assert_has_calls(
            [mock.call(file) for file in expected_files_to_be_removed], any_order=True
        )
        mock_remove.assert_has_calls(
            [mock.call(file) for file in expected_files_to_be_removed], any_order=True
        )
        mock_open.assert_called_once_with("/etc/cron.weekly/charm-logrotate", "w")
        mock_handle.write.assert_called_once_with(
            dedent(
                """\
                #!/bin/bash
                /usr/bin/sudo /usr/bin/juju-run unit-logrotated/0 "/mock/unit-logrotated-0/.venv/bin/python3 /mock/unit-logrotated-0/charm/lib/lib_cron.py"
                """  # noqa
            )
        )
        mock_chmod.assert_called_once_with("/etc/cron.weekly/charm-logrotate", 0o755)

    def test_install_cronjob_removes_etc_config_when_cronjob_disabled(
        self, cron, mocker
    ):
        """Test that all cronjob related files created upon cronjobs being disabled."""
        mock_exists = mocker.patch("lib_cron.os.path.exists", return_value=True)
        mock_remove = mocker.patch("lib_cron.os.remove")

        expected_files_to_be_removed = [
            "/etc/cron.hourly/charm-logrotate",
            "/etc/cron.daily/charm-logrotate",
            "/etc/cron.weekly/charm-logrotate",
            "/etc/cron.monthly/charm-logrotate",
            "/etc/logrotate_cronjob_config",
        ]
        cron_config = cron()
        cron_config.cronjob_enabled = False
        cron_config.install_cronjob()

        mock_exists.assert_has_calls(
            [mock.call(file) for file in expected_files_to_be_removed], any_order=True
        )
        mock_remove.assert_has_calls(
            [mock.call(file) for file in expected_files_to_be_removed], any_order=True
        )
