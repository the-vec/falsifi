"""
Falsifi - Refutation Bounty Platform
Main Flask Application
"""
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models import db, User, Bounty, Refutation, LeaderboardEntry, BountyStatus, AdjudicationStatus
from ai_adjudicator import AIAdjudicator

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///falsifi.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
adjudicator = AIAdjudicator()

# Context processor for template globals
@app.context_processor
def inject_globals():
    return {
        'now': datetime.utcnow(),
        'current_user': get_current_user()
    }

# Custom Jinja2 filter for newlines to <br>
@app.template_filter('nl2br')
def nl2br_filter(text):
    if text:
        return text.replace('\n', '<br>\n')
    return text

def get_current_user():
    """Get current user from session. For MVP, we use a simple user_id in session."""
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def require_login():
    """Check if user is logged in."""
    user = get_current_user()
    if not user:
        flash('Please log in to continue', 'warning')
        return redirect(url_for('login'))
    return None

# ============== HOME & AUTH ==============

@app.route('/')
def index():
    """Home page with featured bounties."""
    featured_bounties = Bounty.query.filter_by(status=BountyStatus.OPEN) \
                                    .order_by(Bounty.created_at.desc()) \
                                    .limit(5).all()
    stats = {
        'total_bounties': Bounty.query.count(),
        'open_bounties': Bounty.query.filter_by(status=BountyStatus.OPEN).count(),
        'total_refutations': Refutation.query.count(),
        'total_users': User.query.count()
    }
    return render_template('index.html', bounties=featured_bounties, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login for MVP."""
    from flask import session
    
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        
        if user:
            session['user_id'] = user.id
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('User not found', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Log out current user."""
    from flask import session
    session.pop('user_id', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new user."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        user = User(username=username, email=email, points=1000)
        db.session.add(user)
        db.session.commit()
        
        from flask import session
        session['user_id'] = user.id
        flash('Account created! Welcome to Falsifi!', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

# ============== BOUNTIES ==============

@app.route('/bounties')
def list_bounties():
    """List all bounties with filtering."""
    status = request.args.get('status', 'all')
    category = request.args.get('category', 'all')
    
    query = Bounty.query
    
    if status == 'open':
        query = query.filter_by(status=BountyStatus.OPEN)
    elif status == 'closed':
        query = query.filter_by(status=BountyStatus.CLOSED)
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    bounties = query.order_by(Bounty.created_at.desc()).all()
    
    # Get unique categories for filter
    categories = db.session.query(Bounty.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('bounties.html', bounties=bounties, 
                          current_status=status, current_category=category,
                          categories=categories)

@app.route('/bounties/<int:bounty_id>')
def view_bounty(bounty_id):
    """View a single bounty with its refutations."""
    bounty = Bounty.query.get_or_404(bounty_id)
    refutations = Refutation.query.filter_by(bounty_id=bounty_id) \
                                  .order_by(Refutation.created_at.desc()).all()
    
    # Calculate some stats
    avg_rating = db.session.query(db.func.avg(Refutation.creator_rating)) \
                          .filter_by(bounty_id=bounty_id).scalar()
    
    can_refute = (bounty.status == BountyStatus.OPEN and 
                  get_current_user() and 
                  get_current_user().id != bounty.creator_id)
    
    is_owner = get_current_user() and get_current_user().id == bounty.creator_id
    
    return render_template('bounty_detail.html', 
                          bounty=bounty, 
                          refutations=refutations,
                          avg_rating=avg_rating,
                          can_refute=can_refute,
                          is_owner=is_owner)

@app.route('/bounties/create', methods=['GET', 'POST'])
def create_bounty():
    """Create a new bounty."""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category', 'general')
        bounty_amount = int(request.form.get('bounty_amount', 100))
        auto_adjudicate = request.form.get('auto_adjudicate') == 'on'
        
        user = get_current_user()
        
        if user.points < bounty_amount:
            flash('Insufficient points for this bounty', 'error')
            return render_template('create_bounty.html')
        
        # Deduct points
        user.points -= bounty_amount
        
        bounty = Bounty(
            title=title,
            description=description,
            category=category,
            bounty_amount=bounty_amount,
            creator_id=user.id,
            auto_adjudicate=auto_adjudicate,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        
        db.session.add(bounty)
        db.session.commit()
        
        flash('Bounty created successfully!', 'success')
        return redirect(url_for('view_bounty', bounty_id=bounty.id))
    
    return render_template('create_bounty.html', user=get_current_user())

@app.route('/bounties/<int:bounty_id>/close', methods=['POST'])
def close_bounty(bounty_id):
    """Close a bounty (creator only)."""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    
    bounty = Bounty.query.get_or_404(bounty_id)
    user = get_current_user()
    
    if bounty.creator_id != user.id:
        flash('Only the bounty creator can close this', 'error')
        return redirect(url_for('view_bounty', bounty_id=bounty_id))
    
    bounty.status = BountyStatus.CLOSED
    
    # Return unclaimed bounty amount to creator
    user.points += bounty.bounty_amount
    
    db.session.commit()
    
    flash('Bounty closed. Unclaimed points returned to you.', 'info')
    return redirect(url_for('view_bounty', bounty_id=bounty_id))

# ============== REFUTATIONS ==============

@app.route('/bounties/<int:bounty_id>/refute', methods=['GET', 'POST'])
def submit_refutation(bounty_id):
    """Submit a refutation to a bounty."""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    
    bounty = Bounty.query.get_or_404(bounty_id)
    user = get_current_user()
    
    if bounty.status != BountyStatus.OPEN:
        flash('This bounty is no longer accepting refutations', 'error')
        return redirect(url_for('view_bounty', bounty_id=bounty_id))
    
    if bounty.creator_id == user.id:
        flash('You cannot refute your own bounty', 'error')
        return redirect(url_for('view_bounty', bounty_id=bounty_id))
    
    if request.method == 'POST':
        content = request.form.get('content')
        sources = request.form.get('sources', '')
        bond_amount = int(request.form.get('bond_amount', 50))
        
        # Check if user has enough points for bond
        if user.points < bond_amount:
            flash(f'Insufficient points for bond. You need {bond_amount} points.', 'error')
            return render_template('submit_refutation.html', bounty=bounty, user=user)
        
        # Deduct bond
        user.points -= bond_amount
        
        # Create refutation
        refutation = Refutation(
            bounty_id=bounty_id,
            author_id=user.id,
            content=content,
            sources=sources,
            bond_amount=bond_amount
        )
        
        db.session.add(refutation)
        db.session.commit()
        
        # AI Adjudication
        if bounty.auto_adjudicate:
            result = adjudicator.evaluate_refutation(
                bounty.title,
                bounty.description,
                content,
                sources
            )
            
            refutation.ai_score = result['score']
            refutation.ai_feedback = result['feedback']
            
            # Map status string to enum
            status_map = {
                'approved': AdjudicationStatus.APPROVED,
                'rejected': AdjudicationStatus.REJECTED,
                'flagged': AdjudicationStatus.FLAGGED
            }
            refutation.adjudication_status = status_map.get(result['status'], AdjudicationStatus.PENDING)
            
            db.session.commit()
            
            if result['status'] == 'rejected':
                flash('Your refutation was auto-rejected for low quality. Bond forfeited.', 'warning')
            elif result['status'] == 'flagged':
                flash('Your refutation has been flagged for human review.', 'warning')
            else:
                flash('Refutation submitted! AI pre-screening passed.', 'success')
        else:
            flash('Refutation submitted and awaiting review!', 'success')
        
        return redirect(url_for('view_bounty', bounty_id=bounty_id))
    
    return render_template('submit_refutation.html', bounty=bounty, user=user)

@app.route('/refutations/<int:refutation_id>/rate', methods=['POST'])
def rate_refutation(refutation_id):
    """Rate a refutation (bounty creator only)."""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    
    refutation = Refutation.query.get_or_404(refutation_id)
    user = get_current_user()
    bounty = refutation.bounty
    
    if bounty.creator_id != user.id:
        flash('Only the bounty creator can rate refutations', 'error')
        return redirect(url_for('view_bounty', bounty_id=bounty.id))
    
    rating = int(request.form.get('rating', 5))
    feedback = request.form.get('feedback', '')
    
    refutation.creator_rating = rating
    refutation.creator_feedback = feedback
    
    # Calculate and award reward
    reward = adjudicator.calculate_reward(
        refutation.ai_score or 50,
        rating,
        bounty.bounty_amount
    )
    refutation.reward_earned = reward
    
    # Award points to refutation author
    refutation.author.points += reward
    
    # Return bond if rated well
    if adjudicator.should_return_bond(refutation.ai_score or 50, rating):
        refutation.author.points += refutation.bond_amount
        refutation.bond_returned = True
    
    # Update author reputation
    update_user_reputation(refutation.author)
    
    db.session.commit()
    
    flash(f'Rating submitted! Author earned {reward} points.', 'success')
    return redirect(url_for('view_bounty', bounty_id=bounty.id))

# ============== DASHBOARD & LEADERBOARD ==============

@app.route('/dashboard')
def dashboard():
    """User dashboard."""
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    
    user = get_current_user()
    
    my_bounties = Bounty.query.filter_by(creator_id=user.id) \
                              .order_by(Bounty.created_at.desc()).all()
    
    my_refutations = Refutation.query.filter_by(author_id=user.id) \
                                     .order_by(Refutation.created_at.desc()).all()
    
    # Calculate stats
    total_earned = sum(r.reward_earned for r in my_refutations)
    avg_received_rating = db.session.query(db.func.avg(Refutation.creator_rating)) \
                                    .filter_by(author_id=user.id) \
                                    .filter(Refutation.creator_rating != None).scalar()
    
    stats = {
        'total_earned': total_earned,
        'avg_rating': round(avg_received_rating, 2) if avg_received_rating else None,
        'refutations_submitted': len(my_refutations),
        'bounties_created': len(my_bounties),
        'current_points': user.points
    }
    
    return render_template('dashboard.html', 
                          user=user,
                          my_bounties=my_bounties,
                          my_refutations=my_refutations,
                          stats=stats)

@app.route('/leaderboard')
def leaderboard():
    """Show leaderboard of top refutation providers."""
    # Update leaderboard cache
    update_leaderboard()
    
    top_users = LeaderboardEntry.query \
        .join(User) \
        .order_by(LeaderboardEntry.total_earned.desc()) \
        .limit(20).all()
    
    return render_template('leaderboard.html', entries=top_users)

def update_leaderboard():
    """Update the leaderboard cache."""
    # Clear old entries
    LeaderboardEntry.query.delete()
    
    # Calculate stats for each user with refutations
    users_with_refutations = db.session.query(User.id).join(Refutation).distinct().all()
    
    for (user_id,) in users_with_refutations:
        stats = db.session.query(
            db.func.count(Refutation.id).label('count'),
            db.func.avg(Refutation.creator_rating).label('avg_rating'),
            db.func.sum(Refutation.reward_earned).label('total_earned')
        ).filter_by(author_id=user_id).first()
        
        entry = LeaderboardEntry(
            user_id=user_id,
            total_refutations=stats.count or 0,
            avg_rating=stats.avg_rating or 0,
            total_earned=stats.total_earned or 0
        )
        db.session.add(entry)
    
    db.session.commit()

def update_user_reputation(user):
    """Update a user's reputation score based on their refutations."""
    stats = db.session.query(
        db.func.avg(Refutation.creator_rating).label('avg_rating'),
        db.func.count(Refutation.id).label('count')
    ).filter_by(author_id=user.id).filter(Refutation.creator_rating != None).first()
    
    if stats.count and stats.count > 0:
        # Normalize to 0-100 scale
        user.reputation_score = (stats.avg_rating / 10) * 100

# ============== API ENDPOINTS ==============

@app.route('/api/bounties')
def api_bounties():
    """API endpoint for bounties."""
    bounties = Bounty.query.order_by(Bounty.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bounties])

@app.route('/api/bounties/<int:bounty_id>')
def api_bounty(bounty_id):
    """API endpoint for single bounty."""
    bounty = Bounty.query.get_or_404(bounty_id)
    data = bounty.to_dict()
    data['refutations'] = [r.to_dict() for r in bounty.refutations]
    return jsonify(data)

# ============== INITIALIZATION ==============

def create_sample_data():
    """Create sample data for demo purposes."""
    # Check if data already exists
    if User.query.first():
        return
    
    print("Creating sample data...")
    
    # Create users
    users = [
        User(username='alice', email='alice@example.com', points=5000),
        User(username='bob', email='bob@example.com', points=3000),
        User(username='charlie', email='charlie@example.com', points=2000),
        User(username='demo_user', email='demo@example.com', points=1000),
    ]
    
    for user in users:
        db.session.add(user)
    
    db.session.commit()
    
    # Create bounties
    bounties = [
        Bounty(
            title='Proof of stake is more secure than proof of work',
            description='''Many cryptocurrency advocates claim that Proof of Stake (PoS) consensus mechanisms are inherently more secure than Proof of Work (PoW). 

The argument typically goes that:
1. PoS requires validators to stake their own tokens, creating economic incentive to act honestly
2. PoS is more energy efficient
3. PoS can achieve faster finality
4. The cost of attacking PoS is higher because attackers would lose their stake

However, critics argue that PoS may have different security properties that could make it more vulnerable to certain types of attacks, such as:
- Long-range attacks
- Nothing-at-stake problems
- Concentration of power among wealthy validators
- Regulatory capture risks

I\'m looking for the strongest possible critique of the security claims of PoS compared to PoW. What are the decisive arguments that PoS is NOT more secure?''',
            category='crypto',
            bounty_amount=500,
            creator_id=users[0].id,
            auto_adjudicate=True
        ),
        Bounty(
            title='Low-fat diets reduce heart disease risk',
            description='''The conventional wisdom for decades has been that low-fat diets reduce the risk of heart disease. This was the basis for the food pyramid and countless dietary recommendations.

Key claims to evaluate:
1. Saturated fat intake is causally linked to heart disease
2. Reducing dietary fat leads to reduced cardiovascular events
3. The mechanism (lipid hypothesis) is well-established

I\'m looking for critiques that examine:
- The quality of evidence supporting these claims
- Confounding factors that may explain observed correlations
- Potential harms of low-fat dietary recommendations
- The role of sugar and refined carbohydrates

Is the low-fat dogma actually supported by the evidence?''',
            category='science',
            bounty_amount=750,
            creator_id=users[1].id,
            auto_adjudicate=True
        ),
        Bounty(
            title='This startup has a viable business model',
            description='''Startup pitch: "EcoTrack" - A mobile app that helps users track their carbon footprint and offers personalized recommendations for reducing it.

Business model claims:
1. Users pay $9.99/month for premium features (detailed tracking, offset marketplace)
2. Carbon offset providers pay commission on sales (15%)
3. Enterprise version for companies to track employee footprint ($50/employee/year)
4. Target: 100k users in year 1, $1M ARR by year 2

Total addressable market: "Everyone concerned about climate change" = potentially billions of users.

I\'m an investor considering a seed round. Tear this apart. Where are the holes in this business model? What assumptions are unfounded? Why might this fail?''',
            category='business',
            bounty_amount=1000,
            creator_id=users[2].id,
            auto_adjudicate=True
        ),
        Bounty(
            title='AI will replace most software engineers by 2030',
            description='''Claim: By 2030, AI systems will be capable of replacing 80%+ of current software engineering jobs.

Arguments for this claim:
1. Current AI coding assistants (Copilot, etc.) already show impressive capabilities
2. Exponential improvement in AI capabilities
3. Economic incentives for automation are massive
4. Software is easier to automate than physical tasks

I\'m looking for strong counter-arguments. What are the limitations that will prevent this from happening? Why might software engineering remain a human-dominated field?''',
            category='technology',
            bounty_amount=600,
            creator_id=users[0].id,
            auto_adjudicate=True
        ),
    ]
    
    for bounty in bounties:
        # Deduct points from creators
        creator = users[bounty.creator_id - 1]
        creator.points -= bounty.bounty_amount
        db.session.add(bounty)
    
    db.session.commit()
    
    # Create sample refutations
    refutations = [
        Refutation(
            bounty_id=1,
            author_id=users[1].id,
            content='''The "economic security" argument for PoS is fundamentally flawed. Here\'s why:

1. **The Nothing-at-Stake Problem**: Unlike PoW where miners must expend real electricity costs, PoS validators can vote on multiple conflicting chains at zero marginal cost. This makes certain attacks (like long-range attacks) much easier in PoS.

2. **Concentration Risk**: PoS naturally leads to centralization. Those with more stake earn more rewards, which compounds over time. Ethereum\'s top 3 staking pools control >50% of stake. This is worse than PoW mining centralization because entry barriers are capital-based rather than infrastructure-based.

3. **Regulatory Capture**: Validators are identifiable entities. Governments can easily compel them to censor transactions or freeze funds. In PoW, miners can relocate or go underground; stakers have their assets frozen on-chain.

4. **The Cost of Attack Fallacy**: While attackers do lose their stake, the cost of *attempting* an attack is much lower than PoW. A 51% attack in PoS requires capital, not ongoing energy expenditure.''',
            sources='https://medium.com/@hugonguyen/proof-of-stake-is-less-secure-than-proof-of-work-here-s-why-7c6b9d8c8b9c',
            bond_amount=50,
            ai_score=85,
            ai_feedback='Strong logical arguments addressing core PoS vulnerabilities. Good use of technical concepts.',
            adjudication_status=AdjudicationStatus.APPROVED
        ),
        Refutation(
            bounty_id=2,
            author_id=users[2].id,
            content='''The low-fat diet hypothesis is one of the most damaging scientific errors in modern history. Here\'s the refutation:

**The Evidence Against:**
- The original Seven Countries Study by Ancel Keys cherry-picked data, excluding countries that didn\'t fit the hypothesis
- The Women\'s Health Initiative ($700M study, 48,000 women) found no reduction in heart disease on low-fat diets
- The PURE study (135,000 people across 18 countries) found that higher saturated fat intake was associated with LOWER mortality

**The Mechanism Problem:**
The lipid hypothesis assumes dietary fat → blood cholesterol → heart disease. But:
- 75% of cholesterol is produced by the body, not from diet
- Dietary cholesterol has minimal impact on blood cholesterol for most people
- The LDL/HDL distinction matters - saturated fat raises both, and the ratio often improves

**The Replacement Problem:**
When people reduce fat, they increase carbs. This leads to:
- Higher triglycerides (stronger heart disease predictor than cholesterol)
- Lower HDL ("good" cholesterol)
- Insulin resistance and metabolic syndrome

The low-fat recommendation may have CAUSED the obesity epidemic by promoting high-carb diets.''',
            sources='https://www.bmj.com/content/347/bmj.f6690; https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(17)32252-3/fulltext',
            bond_amount=75,
            ai_score=92,
            ai_feedback='Excellent use of large-scale studies. Cites specific evidence. Addresses causal mechanisms well.',
            adjudication_status=AdjudicationStatus.APPROVED,
            creator_rating=9,
            creator_feedback='Very thorough, brought studies I hadn\'t seen.',
            reward_earned=675,
            bond_returned=True
        ),
    ]
    
    for ref in refutations:
        ref.author.points += ref.reward_earned
        if ref.bond_returned:
            ref.author.points += ref.bond_amount
        db.session.add(ref)
    
    db.session.commit()
    print("Sample data created successfully!")

@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        create_sample_data()
        print("Database initialized!")

# Create tables on startup
with app.app_context():
    db.create_all()
    create_sample_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)