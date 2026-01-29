import pandas as pd
df = pd.read_json('mydb.Enrich_logs.json', orient='records')
df.head()
df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    format='mixed',
    errors='coerce',
    utc=True
)
df = df.drop(columns=["_id"])
df_rec = df[df['action'] == 'view_product']
import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import combinations
from math import sqrt


class ItemItemCooccurrence:
    def __init__(self, session_gap_minutes=30, min_cooccurrence=1):
        self.session_gap = pd.Timedelta(minutes=session_gap_minutes)
        self.min_cooccurrence = min_cooccurrence

        self.cooccurrence = defaultdict(float)
        self.item_counts = defaultdict(int)
        self.similarity = defaultdict(dict)

    def _build_sessions(self, df):
        df = df.sort_values(["user_id", "timestamp"])

        sessions = []
        current_session = []
        last_user = None
        last_time = None

        for row in df.itertuples(index=False):
            if (
                row.user_id != last_user
                or last_time is None
                or row.timestamp - last_time > self.session_gap
            ):
                if current_session:
                    sessions.append(set(current_session))
                current_session = [row.item_id]
            else:
                current_session.append(row.item_id)

            last_user = row.user_id
            last_time = row.timestamp

        if current_session:
            sessions.append(set(current_session))

        return sessions

    def fit(self, df):
        sessions = self._build_sessions(df)

        for items in sessions:
            for item in items:
                self.item_counts[item] += 1

            for i, j in combinations(sorted(items), 2):
                self.cooccurrence[(i, j)] += 1
                self.cooccurrence[(j, i)] += 1

        self._compute_similarity()

    def _compute_similarity(self):
        for (i, j), cij in self.cooccurrence.items():
            if cij < self.min_cooccurrence:
                continue

            denom = sqrt(self.item_counts[i] * self.item_counts[j])
            if denom == 0:
                continue

            sim = cij / denom
            self.similarity[i][j] = sim

    def recommend(self, item_id, k=10):
        if item_id not in self.similarity:
            return "No recommendations available."

        return sorted(
            self.similarity[item_id].items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]
model = ItemItemCooccurrence()
model.fit(df_rec)
res = model.recommend(item_id='iphone-16', k=10)
print(res)