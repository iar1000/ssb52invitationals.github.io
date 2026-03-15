#!/usr/bin/env python3
"""
Script to update README.md with tournament statistics from CSV result files.
"""

import csv
import os
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# Player name abbreviations mapping
PLAYER_ABBREV = {
    'rico': 'RT',
    'linus': 'LS',
    'pius': 'PK',
    'markus': 'MM',
    'basil': 'BG',
    'noah': 'NG',
    'patson': 'PS',
    'marco': 'Maf',
    'luca': 'LG',
    'dano': 'DH',
    'ferdi': 'FerG',
    'rayan': 'RA',
    'felix': 'FX',
    'sean': 'SN',
    'max': 'MX',
}

# Arena/location mapping by date
ARENA_INFO = {
    '2023-04-10': 'in the planted arena',
    '2023-04-23': 'underneath the legendary steve\'s livingroom arena',
    '2024-05-18': 'in the planted arena',
    '2024-11-09': 'in the planted arena',
    '2025-11-15': 'in the planted arena',
    '2026-03-14': 'in rolands backyard arena',
}


def get_weekday(date_str):
    """Get the weekday name from a date string."""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    return date.strftime('%A').lower()


def format_date(date_str):
    """Format date as 'weekday, DD. Month YYYY'."""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    day = date.day
    month = date.strftime('%B')
    # German month abbreviations
    month_map = {
        'January': 'Jan', 'February': 'Feb', 'March': 'Mar', 'April': 'April',
        'May': 'Mai', 'June': 'Jun', 'July': 'Jul', 'August': 'Aug',
        'September': 'Sep', 'October': 'Oct', 'November': 'Nov', 'December': 'Dec'
    }
    month_abbrev = month_map.get(month, month)
    weekday = get_weekday(date_str)
    return f"**{weekday}, {day:02d}. {month_abbrev} {date.year}**"


def get_player_abbrev(name):
    """Get the abbreviation for a player name."""
    return PLAYER_ABBREV.get(name.lower(), name)


def load_tournament_data(results_dir):
    """Load all tournament data from CSV files."""
    tournaments = {}
    
    # Find all tournament files (not players files)
    for filename in os.listdir(results_dir):
        if filename.endswith('.csv') and '_players' not in filename:
            date_str = filename.split('_')[0]
            filepath = os.path.join(results_dir, filename)
            
            # Load corresponding players file
            players_file = None
            for pf in os.listdir(results_dir):
                if pf.startswith(date_str) and '_players' in pf:
                    players_file = os.path.join(results_dir, pf)
                    break
            
            # Read players
            players = []
            if players_file and os.path.exists(players_file):
                with open(players_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('player'):
                            players.append(row['player'].strip())
            
            # Read match data
            matches = []
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    matches.append({
                        'match_id': int(row['match_id']),
                        'player': row['player'].strip(),
                        'rank': int(row['rank']),
                        'kills': int(row['kills'])
                    })
            
            tournaments[date_str] = {
                'players': players,
                'matches': matches
            }
    
    return tournaments


def calculate_tournament_stats(tournament_data):
    """Calculate statistics for a single tournament."""
    players = tournament_data['players']
    matches = tournament_data['matches']
    
    # Initialize stats per player
    player_stats = defaultdict(lambda: {
        'games': 0,
        'total_pts': 0,
        'total_kills': 0,
        'ranks': {1: 0, 2: 0, 3: 0, 4: 0}
    })
    
    # Points system: 1st = 3pts, 2nd = 2pts, 3rd = 1pt, 4th = 0pts
    points_map = {1: 3, 2: 2, 3: 1, 4: 0}
    
    for match in matches:
        player = match['player']
        rank = match['rank']
        kills = match['kills']
        
        player_stats[player]['games'] += 1
        player_stats[player]['total_pts'] += points_map.get(rank, 0)
        player_stats[player]['total_kills'] += kills
        if rank in player_stats[player]['ranks']:
            player_stats[player]['ranks'][rank] += 1
    
    # Calculate averages and determine rankings
    results = {}
    for player in players:
        if player not in player_stats or player_stats[player]['games'] == 0:
            continue
        stats = player_stats[player]
        games = stats['games']
        results[player] = {
            'avg_pts': round(stats['total_pts'] / games, 2),
            'avg_kills': round(stats['total_kills'] / games, 2),
            'games': games,
            'first': stats['ranks'][1],
            'second': stats['ranks'][2],
            'third': stats['ranks'][3],
            'fourth': stats['ranks'][4],
            'total_pts': stats['total_pts'],
            'total_kills': stats['total_kills']
        }
    
    # Determine top 3 rankings based on avg_pts
    sorted_players = sorted(results.items(), key=lambda x: x[1]['avg_pts'], reverse=True)
    for i, (player, _) in enumerate(sorted_players[:3]):
        results[player]['tournament_rank'] = i + 1
    
    # Calculate average games per player
    if results:
        avg_games = round(sum(r['games'] for r in results.values()) / len(results))
    else:
        avg_games = 0
    
    return results, avg_games


def calculate_global_stats(tournaments):
    """Calculate global statistics across all tournaments."""
    global_stats = defaultdict(lambda: {
        'tournaments': 0,
        'games': 0,
        'total_pts': 0,
        'total_kills': 0,
        'ranks': {1: 0, 2: 0, 3: 0, 4: 0},
        'tournament_wins': 0,
        'tournament_seconds': 0,
        'tournament_thirds': 0
    })
    
    points_map = {1: 3, 2: 2, 3: 1, 4: 0}
    
    for date_str, data in tournaments.items():
        # Get tournament stats to determine tournament rankings
        tournament_results, _ = calculate_tournament_stats(data)
        
        # Track which players participated in this tournament
        tournament_players = set()
        
        for match in data['matches']:
            player = match['player']
            rank = match['rank']
            kills = match['kills']
            
            tournament_players.add(player)
            global_stats[player]['games'] += 1
            global_stats[player]['total_pts'] += points_map.get(rank, 0)
            global_stats[player]['total_kills'] += kills
            if rank in global_stats[player]['ranks']:
                global_stats[player]['ranks'][rank] += 1
        
        # Count tournament participations
        for player in tournament_players:
            global_stats[player]['tournaments'] += 1
        
        # Count tournament placements
        for player, stats in tournament_results.items():
            if 'tournament_rank' in stats:
                if stats['tournament_rank'] == 1:
                    global_stats[player]['tournament_wins'] += 1
                elif stats['tournament_rank'] == 2:
                    global_stats[player]['tournament_seconds'] += 1
                elif stats['tournament_rank'] == 3:
                    global_stats[player]['tournament_thirds'] += 1
    
    # Calculate averages
    results = {}
    for player, stats in global_stats.items():
        if stats['games'] == 0:
            continue
        results[player] = {
            'tournaments': stats['tournaments'],
            'games': stats['games'],
            'avg_pts': round(stats['total_pts'] / stats['games'], 2),
            'avg_kills': round(stats['total_kills'] / stats['games'], 2),
            'total_kills': stats['total_kills'],
            'first': stats['ranks'][1],
            'second': stats['ranks'][2],
            'third': stats['ranks'][3],
            'fourth': stats['ranks'][4],
            'tournament_wins': stats['tournament_wins'],
            'tournament_seconds': stats['tournament_seconds'],
            'tournament_thirds': stats['tournament_thirds'],
        }
    
    return results


def generate_tournament_table(date_str, players, stats, avg_games):
    """Generate a markdown table for a tournament."""
    arena = ARENA_INFO.get(date_str, 'at a secret place')
    date_formatted = format_date(date_str)
    
    # Filter out players with no games and sort by avg_pts descending
    active_players = [p for p in players if p in stats and stats[p]['games'] > 0]
    active_players = sorted(active_players, key=lambda p: stats[p]['avg_pts'], reverse=True)
    
    if not active_players:
        return ""
    
    # Build header row with player abbreviations
    header = "|                   |"
    for player in active_players:
        header += f" {get_player_abbrev(player)}     \t|"
    header += "   "
    
    # Separator row
    sep = "|----------         |"
    for _ in active_players:
        sep += ":-----:    |"
    sep += "  "
    
    # Average points row
    avg_pts_row = "| ***avg. pts***    |"
    for player in active_players:
        avg_pts_row += f"  {stats[player]['avg_pts']}      |"
    avg_pts_row += "  "
    
    # Average kills row
    avg_kills_row = "| ***avg. kills***  |"
    for player in active_players:
        avg_kills_row += f" {stats[player]['avg_kills']}      |"
    avg_kills_row += "  "
    
    # Rank row
    rank_row = "| ***rank***        |"
    for player in active_players:
        if 'tournament_rank' in stats[player]:
            rank = stats[player]['tournament_rank']
            rank_row += f"  ***{rank}.*** |"
        else:
            rank_row += "           |"
    rank_row += "  "
    
    # Empty separator row
    empty_row = "|                   |"
    for _ in active_players:
        empty_row += "           |"
    empty_row += " "
    
    # Position rows
    first_row = "|***first***        |"
    for player in active_players:
        first_row += f" {stats[player]['first']}         |"
    
    second_row = "|***second***       |"
    for player in active_players:
        second_row += f" {stats[player]['second']}         |"
    
    third_row = "|***third***        |"
    for player in active_players:
        third_row += f" {stats[player]['third']}         |"
    
    table = f"""{date_formatted}, tournament was conducted {arena}. an average of {avg_games} games was played per player.

{header}
{sep}
{avg_pts_row}
{avg_kills_row}
{rank_row}
{empty_row}
{first_row}
{second_row}
{third_row}

"""
    return table


def generate_global_stats_table(global_stats):
    """Generate a markdown table for global statistics."""
    # Sort players by tournament placement points: 1st = 3pts, 2nd = 2pts, 3rd = 1pt
    # Tie-breaker: avg_pts
    def calc_tournament_points(stats):
        return stats['tournament_wins'] * 3 + stats['tournament_seconds'] * 2 + stats['tournament_thirds'] * 1
    
    sorted_players = sorted(global_stats.items(), key=lambda x: (calc_tournament_points(x[1]), x[1]['avg_pts']), reverse=True)
    
    lines = []
    lines.append("| Player | Tournaments | Games | Avg Pts | Avg Kills | Total Kills | 🥇 | 🥈 | 🥉 | 1st | 2nd | 3rd |")
    lines.append("|:-------|:-----------:|:-----:|:-------:|:---------:|:-----------:|:--:|:--:|:--:|:---:|:---:|:---:|")
    
    for player, stats in sorted_players:
        abbrev = get_player_abbrev(player)
        lines.append(
            f"| {abbrev} | {stats['tournaments']} | {stats['games']} | {stats['avg_pts']} | "
            f"{stats['avg_kills']} | {stats['total_kills']} | {stats['tournament_wins']} | {stats['tournament_seconds']} | "
            f"{stats['tournament_thirds']} | {stats['first']} | {stats['second']} | {stats['third']} |"
        )
    
    return "\n".join(lines)


def generate_readme(tournaments, global_stats):
    """Generate the complete README content."""
    # Sort tournaments by date descending
    sorted_dates = sorted(tournaments.keys(), reverse=True)
    
    content = """# global ranking

*Statistics across all tournaments. 🥇🥈🥉 = tournament placements, 1st-4th = match placements.*
*Sorted by tournament placement points (🥇=3pts, 🥈=2pts, 🥉=1pt).*

"""
    
    content += generate_global_stats_table(global_stats)
    content += "\n\n\n## tournaments\n"
    
    for date_str in sorted_dates:
        data = tournaments[date_str]
        stats, avg_games = calculate_tournament_stats(data)
        table = generate_tournament_table(date_str, data['players'], stats, avg_games)
        content += table
    
    content += """

# tracking app
## setup
setup the python environment.  
run `streamlit run app/app.py` to start the app.  
create the tournament and track the results.  
run `python update_readme.py` to update the README with the latest stats.  
push the changes to github to share the results with the community.  

## tracking results
add all the players that play in the tournament.
you can select players that previously participated in the tournament or add new players.
after that, you can start tracking the results of the tournament.
in the tournaments tab, create a pairing and enter the results of the match.
after saving the match, the statistics in the statistics tab will be automatically updated.

# history
The K4 Super Smash Bros Invitationals is a legendary tournament that has been held by the SSB.52 group since its inception in January 4. 2014. The tournament attracts the best players from all over the world who come to compete for gold and glory. The first K4 Super Smash Bros Invitational was a small affair, with only a few players attending. However, after the move from 52 to 4 it gained popularity, quickly attracting the best players from all of the region. 
Over the years, the K4 Super Smash Bros Invitationals has become known for its fierce competition and high level of skill. Many of the top players in the world have competed in the tournament, and it has become a showcase for some of the most exciting and innovative gameplay in the Super Smash Bros. community.  
The tournament has become a must-attend event for players and fans alike, and it has helped to cement Super Smash Bros. N64 as one of the most exciting and dynamic competitive gaming communities in the world.
![](content/group-wide.png)
***figure:*** *ssb52 at the annual board meeting on hyrule castle (2021)*
"""
    
    return content


def main():
    """Main function to update the README."""
    script_dir = Path(__file__).parent
    results_dir = script_dir / 'results'
    readme_path = script_dir / 'README.md'
    
    print("Loading tournament data...")
    tournaments = load_tournament_data(results_dir)
    print(f"Found {len(tournaments)} tournaments")
    
    print("Calculating global statistics...")
    global_stats = calculate_global_stats(tournaments)
    
    print("Generating README...")
    content = generate_readme(tournaments, global_stats)
    
    print(f"Writing to {readme_path}...")
    with open(readme_path, 'w') as f:
        f.write(content)
    
    print("Done!")


if __name__ == '__main__':
    main()
