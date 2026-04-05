import json

from app.engine import _id, _now, _ts, check_meal_goal_mismatch

def test_meal_log_without_meal_profile_is_ignored(db_conn):
    db_conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_weight_01'")
    db_conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_weight_01",
            "meal_logged",
            json.dumps({"visible_food_summary": "The photo appears to show a plated meal."}),
            _ts(_now()),
        ),
    )
    db_conn.commit()

    candidate = check_meal_goal_mismatch(db_conn, "member_weight_01")
    assert candidate is None


def test_one_step_meal_input_is_trusted(db_conn):
    db_conn.execute("UPDATE members SET goal_type = 'low_carb' WHERE id = 'member_weight_01'")
    db_conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            _id(),
            "member_weight_01",
            "meal_logged",
            json.dumps(
                {
                    "meal_profile": "higher_carb",
                    "visible_food_summary": "The photo appears to show a pasta dish with bread.",
                }
            ),
            _ts(_now()),
        ),
    )
    db_conn.commit()

    candidate = check_meal_goal_mismatch(db_conn, "member_weight_01")
    assert candidate is not None
    assert "higher carb" in candidate.explanation_basis
