# app.py

import os
from flask import Flask, render_template, request, redirect, flash
import openai
import sqlite3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", "your_default_secret_key"
)  # Replace with your own secret key

# Configure OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Database configuration
DATABASE = "valorant_players.db"


def get_db_connection():
    """
    Establishes a connection to the SQLite database.

    Returns:
        conn (sqlite3.Connection): SQLite database connection.
    """
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    return conn


# Define role categories
ROLE_CATEGORIES = {
    "Duelist": ["Jett", "Phoenix", "Reyna", "Raze", "Yoru", "Neon"],
    "Sentinel": ["Sage", "Cypher", "Killjoy", "Viper"],
    "Controller": ["Omen", "Astra", "Brimstone", "Viper"],
    "Initiator": ["Sova", "Breach", "Skye", "KAY/O", "Fade"],
}


def assign_role(agent):
    """
    Assigns a role based on the agent name.

    Args:
        agent (str): Name of the agent.

    Returns:
        str: Assigned role (Duelist, Sentinel, Controller, Initiator, or Undefined).
    """
    for role, agents in ROLE_CATEGORIES.items():
        if agent in agents:
            return role
    return "Undefined"


def build_prompt(team_type, additional_constraints, players):
    """
    Builds the prompt to send to OpenAI based on the team type and constraints.

    Args:
        team_type (str): Description of the team submission type.
        additional_constraints (str): Any additional constraints provided by the user.
        players (list of dict): List of player data dictionaries.

    Returns:
        str: The constructed prompt.
    """
    # Convert player data to a readable format
    player_info = ""
    for player in players:
        role = assign_role(player["agent"])
        player_info += (
            f"Player Name: {player['player']}\n"
            f"Organization: {player['org']}\n"
            f"Rounds Played: {player['rds']}\n"
            f"Average Combat Score: {player['average_combat_score']}\n"
            f"Kill/Death Ratio: {player['kill_deaths']}\n"
            f"Average Damage Per Round: {player['average_damage_per_round']}\n"
            f"Kills Per Round: {player['kills_per_round']}\n"
            f"Assists Per Round: {player['assists_per_round']}\n"
            f"First Kills Per Round: {player['first_kills_per_round']}\n"
            f"First Deaths Per Round: {player['first_deaths_per_round']}\n"
            f"Headshot Percentage: {player['headshot_percentage']}%\n"
            f"Clutch Success Percentage: {player['clutch_success_percentage']}%\n"
            f"Clutches Won/Played: {player['clutch_won_played']:.2f}\n"
            f"Total Kills: {player['total_kills']}\n"
            f"Total Deaths: {player['total_deaths']}\n"
            f"Total Assists: {player['total_assists']}\n"
            f"Total First Kills: {player['total_first_kills']}\n"
            f"Total First Deaths: {player['total_first_deaths']}\n"
            f"Map ID: {player['map_id']}\n"
            f"Agent: {player['agent']} ({role})\n"
            # f"Region: {player['region'].upper()}\n"
            f"Region: {player['region']}\n"
            "-----\n"
        )

    prompt = (
        f"Build a team for a VALORANT esports team based on the following player data:\n\n"
        f"{player_info}\n\n"
        f"Team Submission Type: {team_type}\n"
    )

    if additional_constraints:
        prompt += f"Additional Constraints: {additional_constraints}\n\n"

    prompt += (
        "For each team composition, perform the following tasks:\n"
        "1. Assign roles to each player on the team and explain their contribution.\n"
        "2. Specify Offensive vs. Defensive roles.\n"
        "3. Categorize each agent (Duelist, Sentinel, Controller, Initiator).\n"
        "4. Assign a team IGL (In-Game Leader) and explain their role as the primary strategist and shotcaller.\n"
        "5. Provide insights on team strategy and hypothesize team strengths and weaknesses.\n"
    )

    return prompt


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Handles the homepage route, allowing users to select team submission types and generate team compositions.

    Returns:
        Rendered HTML template.
    """
    if request.method == "POST":
        team_type = request.form.get("team_type")
        additional_constraints = request.form.get("additional_constraints", "").strip()

        if not team_type:
            flash("Please select a team submission type.")
            return redirect(request.url)

        # Connect to the database and fetch relevant players based on team_type
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if team_type == "Professional Team Submission":
                # All existing organizations
                query = """
                SELECT * FROM players
                WHERE org IN ('Ascend', 'Mystic', 'Legion', 'Phantom', 'Rising', 'Nebula', 'OrgZ', 'T1A')
                """

                # query = """
                # SELECT * FROM players
                # """
            elif team_type == "Semi-Professional Team Submission":
                # Modify or remove this if no semi-professional orgs exist
                # For example, target 'Rising' as semi-professional
                query = """
                SELECT * FROM players
                WHERE org = 'Rising'
                """
            elif team_type == "Game Changers Team Submission":
                # If 'Game Changers' orgs exist, list them; else, adjust accordingly
                # Assuming 'OrgZ' represents 'Game Changers'
                query = """
                SELECT * FROM players
                WHERE org = 'OrgZ'
                """
            elif team_type == "Mixed-Gender Team Submission":
                # With only one player from 'OrgZ', adjust constraint to at least one
                query = """
                SELECT * FROM players
                WHERE org = 'OrgZ'
                LIMIT 1
                """
            elif team_type == "Cross-Regional Team Submission":
                # Adjust regions to match your data: 'Japan', 'Russia', 'China', 'ME', 'LATAM'
                query = """
                SELECT * FROM players
                WHERE region IN ('Japan', 'Russia', 'China', 'ME', 'LATAM')
                LIMIT 3
                """
            elif team_type == "Rising Star Team Submission":
                # Targeting 'Rising' organization
                query = """
                SELECT * FROM players
                WHERE org = 'Rising'
                """
            else:
                flash("Invalid team submission type selected.")
                return redirect(request.url)

            cursor.execute(query)
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                flash("No players found matching the selected criteria.")
                return redirect(request.url)

            # Convert rows to list of dicts
            players = [dict(row) for row in rows]

            # If Mixed-Gender Team Submission or Cross-Regional Team Submission, ensure constraints
            if team_type == "Mixed-Gender Team Submission":
                # Ensure at least one player from OrgZ
                orgZ_players = [p for p in players if p["org"] == "OrgZ"]
                if len(orgZ_players) < 1:
                    flash(
                        "Not enough players from underrepresented groups (OrgZ) to build a Mixed-Gender team."
                    )
                    return redirect(request.url)
            elif team_type == "Cross-Regional Team Submission":
                # Ensure players are from at least three different regions
                print("xyz")
                regions = set(p["region"].upper() for p in players if p["region"])
                print("xyz")
                if len(regions) < 3:
                    flash(
                        "Not enough players from different regions to build a Cross-Regional team."
                    )
                    return redirect(request.url)

            # Build the prompt for OpenAI
            prompt = build_prompt(team_type, additional_constraints, players)
            print(players)
            print(prompt)
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",  # or "gpt-3.5-turbo"
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in VALORANT team compositions and strategies.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1500,  # Adjust based on desired response length
                    temperature=0.7,
                )
                report_text = response["choices"][0]["message"]["content"].strip()
                print(report_text)
                return render_template("result.html", team_composition=report_text)

            except Exception as e:
                flash(f"An error occurred while generating the team: {e}")
                return redirect(request.url)

        except Exception as e:
            conn.close()
            flash(f"An error occurred while querying the database: {e}")
            return redirect(request.url)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
