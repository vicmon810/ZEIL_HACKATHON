
from anomaly_detector import is_bottleneck

# previous_count, next_count, expected_flag
TEST_CASES = [
    (100, 10, True),
    (100, 29, True),
    (100, 30, False),
    (100, 60, False),
    (100, 95, False),
    (20, 2, True),
    (20, 6, False),
    (9, 0, False),
    (10, 2, True),
    (10, 3, False),
    (120,2,True),
    (33,1,True),
    (10,8,True)
]


def evaluate():
    passed = 0

    for i, (previous, following, expected) in enumerate(
        TEST_CASES, start=1
    ):
        actual = is_bottleneck(previous, following)
        correct = actual == expected
        passed += int(correct)

        print(
            f"Test {i:02d}: "
            f"expected={expected}, actual={actual} "
            f"=> {'PASS' if correct else 'FAIL'}"
        )

    score = passed / len(TEST_CASES)
    print(f"\nDetection accuracy: {score:.1%}")
    print(f"Passed: {passed}/{len(TEST_CASES)}")

    if passed != len(TEST_CASES):
        raise SystemExit(1)


if __name__ == "__main__":
    evaluate()
