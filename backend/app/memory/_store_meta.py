"""schema_meta key/value + reflection / turn-analysis concurrency locks."""

from __future__ import annotations

from backend.app.memory.database import connect


class MetaMixin:
    def get_meta(self, key: str, default: str | None = None) -> str | None:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return default
        return str(row["value"])

    def set_meta(self, key: str, value: str) -> None:
        with connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def note_llm_turn(self) -> int:
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'turns_since_reflection'",
            ).fetchone()
            current = int(row["value"]) if row else 0
            new_count = current + 1
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES ('turns_since_reflection', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (str(new_count),),
            )
        return new_count

    def claim_reflection(self, threshold: int) -> bool:
        with connect(self.db_path) as connection:
            turns_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'turns_since_reflection'",
            ).fetchone()
            reflecting_row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = 'reflecting'",
            ).fetchone()
            turns = int(turns_row["value"]) if turns_row else 0
            reflecting = reflecting_row["value"] if reflecting_row else "0"
            if reflecting != "1" and turns >= threshold:
                connection.execute(
                    """
                    INSERT INTO schema_meta(key, value) VALUES ('reflecting', '1')
                    ON CONFLICT(key) DO UPDATE SET value = '1'
                    """
                )
                connection.execute(
                    """
                    INSERT INTO schema_meta(key, value) VALUES ('turns_since_reflection', '0')
                    ON CONFLICT(key) DO UPDATE SET value = '0'
                    """
                )
                return True
            return False

    def release_reflection(self) -> None:
        self.set_meta("reflecting", "0")

    @staticmethod
    def _turn_analyzing_key(room_id: str) -> str:
        return f"turn_analyzing:{room_id.strip()}"

    def claim_turn_analysis(self, room_id: str) -> bool:
        key = self._turn_analyzing_key(room_id)
        with connect(self.db_path) as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key = ?",
                (key,),
            ).fetchone()
            if row and str(row["value"]) == "1":
                return False
            connection.execute(
                """
                INSERT INTO schema_meta(key, value) VALUES (?, '1')
                ON CONFLICT(key) DO UPDATE SET value = '1'
                """,
                (key,),
            )
            return True

    def release_turn_analysis(self, room_id: str) -> None:
        self.set_meta(self._turn_analyzing_key(room_id), "0")
