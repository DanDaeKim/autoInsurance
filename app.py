from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///claims.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Claim model
class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claimant_name = db.Column(db.String(100), nullable=False)
    claim_amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500))
    score = db.Column(db.Float, default=0)
    filed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Claim {self.claimant_name} - {self.claim_amount}>"

def optimize_claim(claim):
    """
    A dummy optimization function that calculates a score.
    In this example the score is simply the claim amount plus
    a bonus based on the description length.
    """
    base_score = claim.claim_amount
    description_bonus = len(claim.description) / 100 if claim.description else 0
    score = base_score + description_bonus
    return score

@app.route('/')
def index():
    # Retrieve and display all claims, sorted by descending score
    claims = Claim.query.order_by(Claim.score.desc()).all()
    return render_template('index.html', claims=claims)

@app.route('/add', methods=['POST'])
def add_claim():
    # Retrieve form data
    claimant_name = request.form['claimant_name']
    try:
        claim_amount = float(request.form['claim_amount'])
    except ValueError:
        claim_amount = 0.0
    description = request.form.get('description', '')

    # Create new claim and compute its score
    claim = Claim(claimant_name=claimant_name,
                  claim_amount=claim_amount,
                  description=description)
    claim.score = optimize_claim(claim)

    # Optionally, you might file claims immediately if their score is very high.
    # For example, here we file any claim whose score is above an arbitrary threshold.
    if claim.score > 1000:  # adjust threshold as needed
        claim.filed = True

    db.session.add(claim)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/optimize')
def optimize():
    """
    This endpoint simulates an optimization algorithm that picks from
    pending (not yet filed) claims the subset that maximizes total score
    while keeping the sum of claim amounts under a specified budget.
    """
    # Example: assume a daily processing budget of $5,000.
    budget = 5000.0  
    pending_claims = Claim.query.filter_by(filed=False).all()

    # Use a knapsack (dynamic programming) algorithm to select the best claims.
    n = len(pending_claims)
    if n == 0:
        return redirect(url_for('index'))

    # For integer arithmetic in DP, convert dollars to cents.
    budget_cents = int(budget * 100)
    amounts = [int(c.claim_amount * 100) for c in pending_claims]
    # Multiply score by 100 to maintain precision (optional)
    scores = [int(c.score * 100) for c in pending_claims]

    # Initialize DP table: dp[i][w] = max score achievable with first i claims and budget w (in cents)
    dp = [[0] * (budget_cents + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(budget_cents + 1):
            if amounts[i - 1] <= w:
                dp[i][w] = max(dp[i - 1][w],
                               dp[i - 1][w - amounts[i - 1]] + scores[i - 1])
            else:
                dp[i][w] = dp[i - 1][w]

    # Backtrack to determine which claims were selected
    selected = []
    w = budget_cents
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(pending_claims[i - 1])
            w -= amounts[i - 1]

    # Mark the selected claims as filed
    for claim in selected:
        claim.filed = True
    db.session.commit()

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Create the database file if it does not exist
    if not os.path.exists('claims.db'):
        db.create_all()
    app.run(debug=True)
