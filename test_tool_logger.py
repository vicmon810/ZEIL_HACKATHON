
import json
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

import tool_logger


def test_log_persistence():
    example = [{
        "tool": "analyze_job",
        "arguments": {"job_id": "JOB001"},
        "result": {"applications": 100},
    }]

    with TemporaryDirectory() as temp:
        log_dir = Path(temp)
        log_file = log_dir / "tool_calls.jsonl"

        with patch.object(tool_logger, "LOG_DIR", log_dir), \
             patch.object(tool_logger, "LOG_FILE", log_file):

            first_id = tool_logger.save_tool_log(example)
            second_id = tool_logger.save_tool_log(example)

            records = [
                json.loads(line)
                for line in log_file.read_text().splitlines()
            ]

            assert len(records) == 2
            assert first_id != second_id
            assert records[0]["tool"] == "analyze_job"
            assert records[0]["result"]["applications"] == 100

    print("PASS: Logs persist and investigations are unique")


if __name__ == "__main__":
    test_log_persistence()
