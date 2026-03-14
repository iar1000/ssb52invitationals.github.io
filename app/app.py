import streamlit as st
import pandas as pd
import os
import re
import random
from datetime import date

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")


def safe_name(name: str) -> str:
    """Convert a tournament name to a filesystem-safe string."""
    return re.sub(r"[^\w\-]", "_", name.strip().lower())


def list_tournaments() -> list[str]:
    """Return tournament names by scanning for *_players.csv files."""
    tournaments = []
    if not os.path.isdir(RESULTS_DIR):
        os.makedirs(RESULTS_DIR, exist_ok=True)
    for f in sorted(os.listdir(RESULTS_DIR)):
        if f.endswith("_players.csv"):
            tournaments.append(f.replace("_players.csv", ""))
    return tournaments


def players_path(tournament: str) -> str:
    return os.path.join(RESULTS_DIR, f"{tournament}_players.csv")


def matches_path(tournament: str) -> str:
    return os.path.join(RESULTS_DIR, f"{tournament}.csv")


def load_players(tournament: str) -> list[str]:
    path = players_path(tournament)
    if not os.path.exists(path):
        return []
    df = pd.read_csv(path)
    return df["player"].tolist()


def save_players(tournament: str, players: list[str]):
    df = pd.DataFrame({"player": players})
    df.to_csv(players_path(tournament), index=False)


def all_known_players() -> set[str]:
    """Collect every player name across all tournament roster files."""
    known: set[str] = set()
    for t in list_tournaments():
        known.update(load_players(t))
    return known


def load_matches(tournament: str) -> pd.DataFrame:
    path = matches_path(tournament)
    if not os.path.exists(path):
        return pd.DataFrame(columns=["match_id", "player", "rank", "kills"])
    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame(columns=["match_id", "player", "rank", "kills"])
    return df


def save_match(tournament: str, match_rows: list[dict]):
    path = matches_path(tournament)
    new_df = pd.DataFrame(match_rows)
    if os.path.exists(path):
        existing = pd.read_csv(path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_csv(path, index=False)

    


def next_match_id(tournament: str) -> int:
    df = load_matches(tournament)
    if df.empty:
        return 1
    return int(df["match_id"].max()) + 1


def compute_pairings(
    players: list[str],
    schedule_type: str,
    matches_df: pd.DataFrame,
) -> list[str]:
    """Compute the next pairing so each player gets a similar number of games.

    Returns a single list of player names for the next match.
    - 'random': pick players with fewest games first, break ties randomly.
    - 'equal skill': group by similar win count.
    - 'top 1 stays' / 'top 2 stay' / 'top 3 stay': top N from last match stay,
       remaining slots filled from players with fewest games.
    """
    group_size = min(4, len(players))

    # Count games already played per player
    games_played: dict[str, int] = {p: 0 for p in players}
    if not matches_df.empty:
        counts = matches_df.groupby("player")["match_id"].nunique()
        for p in players:
            games_played[p] = int(counts.get(p, 0))

    eligible = list(players)
    # Random: prioritize players with fewest games, shuffle within ties
    by_played: dict[int, list[str]] = {}
    for p in eligible:
        by_played.setdefault(games_played[p], []).append(p)
    ordered = []
    for g in sorted(by_played):
        group = by_played[g]
        random.shuffle(group)
        ordered.extend(group)
    eligible = ordered

    pairing = eligible[:group_size]
    if len(pairing) < 2:
        return []
    return pairing


def create_tournament(name: str):
    slug = f"{date.today().isoformat()}_{safe_name(name)}"
    save_players(slug, [])
    pd.DataFrame(columns=["match_id", "player", "rank", "kills"]).to_csv(
        matches_path(slug), index=False
    )
    return slug


# ── Streamlit App ────────────────────────────────────────────────────────────

st.set_page_config(page_title="SSB N64 Tournament Tracker", layout="wide")
active_tournament = st.session_state.get("active_tournament") or "-"
st.title(f"🎮 K4 Super Smash Bros. N64 — Tournament {active_tournament}")

# ── Sidebar: Tournament Selection / Creation ─────────────────────────────────

st.sidebar.header("Tournament")

tournaments = list_tournaments()

# Load existing tournament
if tournaments:
    options = [""] + tournaments
    active = st.session_state.get("active_tournament")
    default_idx = options.index(active) if active in options else 0
    chosen = st.sidebar.selectbox(
        "Select tournament", options, index=default_idx, key="tournament_select"
    )
    if st.sidebar.button("Load tournament"):
        if chosen:
            st.session_state["active_tournament"] = chosen
            st.rerun()
        else:
            st.sidebar.error("Select a tournament first.")
else:
    st.sidebar.info("No tournaments yet. Create one below.")

# Create new tournament
st.sidebar.subheader("Create new tournament")
new_name = st.sidebar.text_input("Tournament name")
if st.sidebar.button("Create tournament"):
    if new_name.strip():
        slug = f"{date.today().isoformat()}_{safe_name(new_name)}"
        if slug in list_tournaments():
            st.sidebar.error("Tournament already exists.")
        else:
            create_tournament(new_name)
            st.session_state["active_tournament"] = slug
            st.rerun()
    else:
        st.sidebar.error("Please enter a name.")

selected = st.session_state.get("active_tournament")

if selected is None:
    st.info("Select and load a tournament, or create a new one in the sidebar.")
    st.stop()

# ── Main area: tabs ──────────────────────────────────────────────────────────

tab_players, tab_tournament, tab_stats = st.tabs(
    ["👥 Players", "🏆 Tournament", "📊 Statistics"]
)

# ── Tab 1: Player Management ────────────────────────────────────────────────

with tab_players:
    st.subheader(f"Players — {selected}")
    players = load_players(selected)
    known = sorted(all_known_players() - set(players))

    # Add known players via multiselect
    if known:
        returning = st.multiselect(
            "Add known players", known, key="returning_player",
            placeholder="Select known players to add"
        )
        if st.button("Add selected players", key="add_returning") and returning:
            players.extend(returning)
            save_players(selected, players)
            st.rerun()

    # Add a brand-new player
    def _on_add_new_player():
        name = st.session_state.new_player_input.strip()
        if not name:
            return
        current = load_players(selected)
        if name not in current:
            current.append(name)
            save_players(selected, current)
        st.session_state.new_player_input = ""

    col_input, col_btn = st.columns([3, 1])
    with col_input:
        st.text_input(
            "New player", key="new_player_input",
            placeholder="Enter new player name",
            on_change=_on_add_new_player,
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add", key="add_new"):
            _on_add_new_player()
            st.rerun()

    # Current roster
    st.markdown("---")
    if players:
        matches_df = load_matches(selected)
        players_with_matches = set(matches_df["player"].unique()) if not matches_df.empty else set()

        for p in players:
            col_name, col_rm = st.columns([4, 1])
            col_name.write(p)
            has_matches = p in players_with_matches
            if col_rm.button("Remove", key=f"rm_{p}", disabled=has_matches):
                players.remove(p)
                save_players(selected, players)
                st.rerun()
            if has_matches:
                col_rm.caption("has matches")
    else:
        st.info("No players added yet.")

# ── Tab 2: Tournament ────────────────────────────────────────────────────────

with tab_tournament:
    players = load_players(selected)

    if len(players) < 2:
        st.warning("Add at least 2 players before running a tournament.")
        st.stop()

    matches_df = load_matches(selected)

    # ── Pairings ─────────────────────────────────────────────────────────────
    st.subheader("Pairings")
    schedule_type = st.radio(
        "Pairing type",
        ["random", "manual"],
        horizontal=True,
    )

    next_pairing = st.session_state.get("next_pairing")

    if schedule_type == "manual":
        manual_selection = st.multiselect(
            "Select players", players, max_selections=4, key="manual_pairing"
        )
        if st.button("Set pairing"):
            if len(manual_selection) >= 2:
                next_pairing = manual_selection
                st.session_state["next_pairing"] = next_pairing
                st.rerun()
            else:
                st.error("Select at least 2 players.")
    else:
        if st.button("Compute pairings"):
            next_pairing = compute_pairings(players, schedule_type, matches_df)
            st.session_state["next_pairing"] = next_pairing

    if not next_pairing:
        next_pairing = compute_pairings(players, schedule_type, matches_df)
        st.session_state["next_pairing"] = next_pairing

    # ── Record Match ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Record a match")

    n = len(next_pairing)
    ranks = {}
    kills = {}
    cols = st.columns(4)
    for slot in range(4):
        with cols[slot]:
            if slot < n:
                p = next_pairing[slot]
                st.markdown(f"**{p}**")
                ranks[p] = st.segmented_control(
                    "Rank", [1, 2, 3, 4], key=f"rank_{slot}"
                )
                kills[p] = st.number_input(
                    "Kills", min_value=0, step=1, key=f"kills_{slot}"
                )
            else:
                st.markdown("**—**")

    rank_values = [ranks[p] for p in next_pairing]
    all_set = all(r is not None for r in rank_values)
    rank_valid = all_set and sorted(rank_values) == list(range(1, n + 1))

    if st.button("Save match"):
        if not all_set:
            st.error("Select a rank for every player.")
        elif not rank_valid:
            st.error(
                f"Ranks must be unique and cover 1–{n}. "
                f"Got: {rank_values}"
            )
        else:
            mid = next_match_id(selected)
            rows = [
                {
                    "match_id": mid,
                    "player": p,
                    "rank": ranks[p],
                    "kills": kills[p],
                }
                for p in next_pairing
            ]
            save_match(selected, rows)
            
            # Keep manual pairing, recompute for other types
            if schedule_type != "manual":
                st.session_state.pop("next_pairing", None)
            
            st.rerun()

    # ── Match History ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Match History")

    if matches_df.empty:
        st.info("No matches played yet.")
    else:
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4th"}
        pts_map = {1: 3, 2: 2, 3: 1, 4: 0}
        for mid in sorted(matches_df["match_id"].unique(), reverse=True):
            match = matches_df[matches_df["match_id"] == mid].sort_values("rank")
            with st.container(border=True):
                header_col, del_col = st.columns([6, 1])
                header_col.markdown(f"**Match #{int(mid)}**")
                if del_col.button("🗑️", key=f"del_match_{int(mid)}"):
                    matches_df = matches_df[matches_df["match_id"] != mid]
                    matches_df.to_csv(matches_path(selected), index=False)
                    st.rerun()
                mcols = st.columns(len(match))
                for i, (_, r) in enumerate(match.iterrows()):
                    rank = int(r["rank"])
                    emoji = rank_emoji.get(rank, f"{rank}th")
                    mcols[i].metric(
                        label=f"{emoji} {r['player']}",
                        value=f"{pts_map.get(rank, 0)} pts",
                        delta=f"{int(r['kills'])} kills",
                        delta_color="off",
                    )

# ── Tab 3: Statistics ────────────────────────────────────────────────────────

with tab_stats:
    st.subheader("Tournament Statistics")
    matches_df = load_matches(selected)

    if matches_df.empty:
        st.info("No matches recorded yet.")
    else:
        players = sorted(matches_df["player"].unique())

        stats: dict[str, dict[str, object]] = {}
        for p in players:
            pdata = matches_df[matches_df["player"] == p]
            total = len(pdata)
            avg_pts = round(
                ((pdata["rank"] == 1).sum() * 3
                 + (pdata["rank"] == 2).sum() * 2
                 + (pdata["rank"] == 3).sum() * 1)
                / total,
                2,
            )
            stats[p] = {
                "Matches": total,
                "Total Pts": int(
                    (pdata["rank"] == 1).sum() * 3
                    + (pdata["rank"] == 2).sum() * 2
                    + (pdata["rank"] == 3).sum() * 1
                ),
                "Avg Pts": avg_pts,
                "Avg Kills": round(pdata["kills"].mean(), 2),
                "Avg Rank": round(pdata["rank"].mean(), 2),
                "1st": int((pdata["rank"] == 1).sum()),
                "2nd": int((pdata["rank"] == 2).sum()),
                "3rd": int((pdata["rank"] == 3).sum()),
                "4th": int((pdata["rank"] == 4).sum()),
            }

        # Rows = stat names, columns = players, sorted by Avg Pts descending
        summary_df = pd.DataFrame(stats)
        col_order = summary_df.loc["Avg Pts"].sort_values(ascending=False).index
        summary_df = summary_df[col_order]
        st.dataframe(summary_df, use_container_width=True)

    # ── World Ranking ────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🌍 World Ranking")

    ranking_mode = st.radio(
        "Ranking mode", ["Total", "Decay (last 4 tournaments)"], horizontal=True,
    )

    all_tournaments = sorted(list_tournaments(), reverse=True)
    if ranking_mode.startswith("Decay"):
        all_tournaments = all_tournaments[:4]

    all_matches = pd.DataFrame(columns=["match_id", "player", "rank", "kills"])
    for t in all_tournaments:
        tdf = load_matches(t)
        if not tdf.empty:
            all_matches = pd.concat([all_matches, tdf], ignore_index=True)

    if all_matches.empty:
        st.info("No matches across any tournament yet.")
    else:
        all_players = sorted(all_matches["player"].unique())
        world_stats: dict[str, dict[str, object]] = {}
        for p in all_players:
            pdata = all_matches[all_matches["player"] == p]
            total = len(pdata)
            world_stats[p] = {
                "Matches": total,
                "Total Pts": int(
                    (pdata["rank"] == 1).sum() * 3
                    + (pdata["rank"] == 2).sum() * 2
                    + (pdata["rank"] == 3).sum() * 1
                ),
                "Avg Pts": round(
                    ((pdata["rank"] == 1).sum() * 3
                     + (pdata["rank"] == 2).sum() * 2
                     + (pdata["rank"] == 3).sum() * 1)
                    / total, 2,
                ),
                "Avg Kills": round(pdata["kills"].mean(), 2),
                "Avg Rank": round(pdata["rank"].mean(), 2),
                "1st": int((pdata["rank"] == 1).sum()),
                "2nd": int((pdata["rank"] == 2).sum()),
                "3rd": int((pdata["rank"] == 3).sum()),
                "4th": int((pdata["rank"] == 4).sum()),
            }

        world_df = pd.DataFrame(world_stats)
        world_order = world_df.loc["Avg Pts"].sort_values(ascending=False).index
        world_df = world_df[world_order]
        st.dataframe(world_df, use_container_width=True)

    # ── Player Performance Over Time ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("📈 Player Performance Over Time")

    all_known = sorted(all_known_players())
    if not all_known:
        st.info("No players found.")
    else:
        import altair as alt

        chosen_players = st.multiselect(
            "Select players", all_known, key="perf_players",
            placeholder="Choose one or more players",
        )

        if not chosen_players:
            st.info("Select at least one player.")
        else:
            tourney_list = sorted(list_tournaments())
            perf_rows = []
            for player in chosen_players:
                for t in tourney_list:
                    tdf = load_matches(t)
                    if tdf.empty:
                        continue
                    pdata = tdf[tdf["player"] == player]
                    if pdata.empty:
                        continue
                    total = len(pdata)
                    avg_pts = round(
                        ((pdata["rank"] == 1).sum() * 3
                         + (pdata["rank"] == 2).sum() * 2
                         + (pdata["rank"] == 3).sum() * 1)
                        / total, 2,
                    )
                    perf_rows.append({
                        "Date": t[:10] if len(t) >= 10 else t,
                        "Player": player,
                        "Avg Pts": avg_pts,
                        "Avg Kills": round(pdata["kills"].mean(), 2),
                    })

            if not perf_rows:
                st.info("No matches found for the selected players.")
            else:
                perf_df = pd.DataFrame(perf_rows)

                pts_chart = alt.Chart(perf_df).mark_line(
                    strokeWidth=2, point=True,
                ).encode(
                    x=alt.X("Date:N", title="Tournament"),
                    y=alt.Y("Avg Pts:Q", title="Value"),
                    color=alt.Color("Player:N"),
                    tooltip=["Date", "Player", "Avg Pts"],
                )

                kills_chart = alt.Chart(perf_df).mark_line(
                    strokeWidth=2, strokeDash=[5, 5], opacity=0.5, point=True,
                ).encode(
                    x=alt.X("Date:N", title="Tournament"),
                    y=alt.Y("Avg Kills:Q", title="Value"),
                    color=alt.Color("Player:N"),
                    tooltip=["Date", "Player", "Avg Kills"],
                )

                chart = (pts_chart + kills_chart).properties(
                    height=400,
                ).interactive()

                st.altair_chart(chart, use_container_width=True)
                st.caption("Solid lines = Avg Pts · Dashed lines (50% opacity) = Avg Kills")
