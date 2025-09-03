"""
Simple Admin Dashboard for Telegram Subscription Bot
No JavaScript frameworks - just HTML/CSS with server-side rendering
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
from urllib.parse import parse_qs

from aiohttp import web
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp_jinja2
import jinja2

from database.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# Admin configuration
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production!
SESSION_SECRET_KEY = os.getenv("SESSION_KEY", secrets.token_bytes(32))

class AdminDashboard:
    """Simple admin dashboard for subscription management"""
    
    def __init__(self, db_client: SupabaseClient, bot=None):
        self.db = db_client
        self.bot = bot
        self.app = web.Application()
        self.setup_app()
        
    def setup_app(self):
        """Configure the web application"""
        # Setup sessions
        setup(self.app, EncryptedCookieStorage(SESSION_SECRET_KEY))
        
        # Setup Jinja2 templates
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.DictLoader(self.get_templates())
        )
        
        # Add routes
        self.app.router.add_get('/', self.index_handler)
        self.app.router.add_get('/login', self.login_page)
        self.app.router.add_post('/login', self.login_handler)
        self.app.router.add_get('/logout', self.logout_handler)
        self.app.router.add_get('/dashboard', self.dashboard_handler)
        self.app.router.add_get('/users', self.users_handler)
        self.app.router.add_post('/user/{telegram_id}/whitelist', self.whitelist_user)
        self.app.router.add_post('/user/{telegram_id}/remove', self.remove_user)
        self.app.router.add_post('/user/{telegram_id}/extend', self.extend_subscription)
        self.app.router.add_get('/stats', self.stats_handler)
        self.app.router.add_get('/export', self.export_csv_handler)
        
    def get_templates(self):
        """Return template dictionary for Jinja2"""
        return {
            'base.html': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin Dashboard{% endblock %}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .nav {
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }
        .nav a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
        .nav a:hover { text-decoration: underline; }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: #f5f5f5;
            font-weight: 600;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.8; }
        .btn-primary { background: #667eea; color: white; }
        .btn-success { background: #48bb78; color: white; }
        .btn-danger { background: #f56565; color: white; }
        .btn-warning { background: #ed8936; color: white; }
        .login-form {
            max-width: 400px;
            margin: 100px auto;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
        }
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 5px;
            font-size: 16px;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge-active { background: #c6f6d5; color: #22543d; }
        .badge-expired { background: #fed7d7; color: #742a2a; }
        .badge-whitelisted { background: #e9d8fd; color: #44337a; }
    </style>
</head>
<body>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>''',
            
            'login.html': '''{% extends "base.html" %}
{% block title %}Login - Admin Dashboard{% endblock %}
{% block content %}
<div class="login-form">
    <div class="card">
        <h2>Admin Login</h2>
        {% if error %}
        <p style="color: red; margin: 10px 0;">{{ error }}</p>
        {% endif %}
        <form method="post" action="/login">
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required autofocus>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Login</button>
        </form>
    </div>
</div>
{% endblock %}''',
            
            'dashboard.html': '''{% extends "base.html" %}
{% block title %}Dashboard - Admin{% endblock %}
{% block content %}
<div class="header">
    <h1>Subscription Bot Admin Dashboard</h1>
    <div class="nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/users">Users</a>
        <a href="/stats">Statistics</a>
        <a href="/export">Export CSV</a>
        <a href="/logout" style="margin-left: auto; color: #f56565;">Logout</a>
    </div>
</div>

<div class="stats-grid">
    <div class="stat-card">
        <div>Total Users</div>
        <div class="stat-value">{{ stats.total_users }}</div>
    </div>
    <div class="stat-card">
        <div>Active Subscriptions</div>
        <div class="stat-value">{{ stats.active_count }}</div>
    </div>
    <div class="stat-card">
        <div>Whitelisted</div>
        <div class="stat-value">{{ stats.whitelisted_count }}</div>
    </div>
    <div class="stat-card">
        <div>Monthly Revenue</div>
        <div class="stat-value">${{ "%.2f"|format(stats.total_revenue_usd) }}</div>
    </div>
</div>

<div class="card">
    <h2>Recent Activity</h2>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>User ID</th>
                <th>Action</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>
            {% for activity in recent_activities %}
            <tr>
                <td>{{ activity.timestamp.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>{{ activity.telegram_id }}</td>
                <td>{{ activity.action }}</td>
                <td>{{ activity.details or '-' }}</td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4">No recent activity</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

<div class="card">
    <h2>Expiring Soon</h2>
    <table>
        <thead>
            <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Expires In</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for user in expiring_users %}
            <tr>
                <td>{{ user.telegram_id }}</td>
                <td>{{ user.username or 'N/A' }}</td>
                <td>{{ user.days_until_expiry() }} days</td>
                <td>
                    <form method="post" action="/user/{{ user.telegram_id }}/extend" style="display: inline;">
                        <button class="btn btn-success">Extend 30 Days</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="4">No subscriptions expiring soon</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}''',
            
            'users.html': '''{% extends "base.html" %}
{% block title %}Users - Admin{% endblock %}
{% block content %}
<div class="header">
    <h1>User Management</h1>
    <div class="nav">
        <a href="/dashboard">Dashboard</a>
        <a href="/users">Users</a>
        <a href="/stats">Statistics</a>
        <a href="/export">Export CSV</a>
        <a href="/logout" style="margin-left: auto; color: #f56565;">Logout</a>
    </div>
</div>

<div class="card">
    <h2>All Users</h2>
    <table>
        <thead>
            <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Status</th>
                <th>Payment Method</th>
                <th>Next Payment</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for user in users %}
            <tr>
                <td>{{ user.telegram_id }}</td>
                <td>{{ user.username or 'N/A' }}</td>
                <td>
                    <span class="badge badge-{{ user.subscription_status }}">
                        {{ user.subscription_status }}
                    </span>
                </td>
                <td>{{ user.payment_method or '-' }}</td>
                <td>{{ user.next_payment_date or '-' }}</td>
                <td>
                    {% if user.subscription_status != 'whitelisted' %}
                    <form method="post" action="/user/{{ user.telegram_id }}/whitelist" style="display: inline;">
                        <button class="btn btn-warning">Whitelist</button>
                    </form>
                    {% endif %}
                    {% if user.subscription_status == 'active' %}
                    <form method="post" action="/user/{{ user.telegram_id }}/extend" style="display: inline;">
                        <button class="btn btn-success">Extend</button>
                    </form>
                    {% endif %}
                    <form method="post" action="/user/{{ user.telegram_id }}/remove" style="display: inline;">
                        <button class="btn btn-danger">Remove</button>
                    </form>
                </td>
            </tr>
            {% else %}
            <tr>
                <td colspan="6">No users found</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}'''
        }
        
    async def check_auth(self, request):
        """Check if user is authenticated"""
        session = await get_session(request)
        return session.get('authenticated', False)
        
    async def index_handler(self, request):
        """Redirect to dashboard or login"""
        if await self.check_auth(request):
            raise web.HTTPFound('/dashboard')
        raise web.HTTPFound('/login')
        
    async def login_page(self, request):
        """Show login page"""
        return aiohttp_jinja2.render_template(
            'login.html', request, {}
        )
        
    async def login_handler(self, request):
        """Handle login form submission"""
        data = await request.post()
        password = data.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session = await get_session(request)
            session['authenticated'] = True
            raise web.HTTPFound('/dashboard')
        
        return aiohttp_jinja2.render_template(
            'login.html', request, {'error': 'Invalid password'}
        )
        
    async def logout_handler(self, request):
        """Logout user"""
        session = await get_session(request)
        session.clear()
        raise web.HTTPFound('/login')
        
    async def dashboard_handler(self, request):
        """Show main dashboard"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        try:
            # Get statistics
            stats = self.db.get_subscription_stats()
            
            # Get recent activities
            recent_activities = self.db.get_recent_activities(limit=10)
            
            # Get expiring subscriptions
            expiring_users = self.db.get_expiring_subscriptions(days=7)
            
            return aiohttp_jinja2.render_template(
                'dashboard.html', 
                request, 
                {
                    'stats': stats,
                    'recent_activities': recent_activities,
                    'expiring_users': expiring_users
                }
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return web.Response(text="Error loading dashboard", status=500)
            
    async def users_handler(self, request):
        """Show all users"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        try:
            users = self.db.get_all_users()
            return aiohttp_jinja2.render_template(
                'users.html',
                request,
                {'users': users}
            )
        except Exception as e:
            logger.error(f"Users page error: {e}")
            return web.Response(text="Error loading users", status=500)
            
    async def whitelist_user(self, request):
        """Whitelist a user"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        telegram_id = int(request.match_info['telegram_id'])
        
        try:
            self.db.whitelist_user(telegram_id)
            raise web.HTTPFound('/users')
        except Exception as e:
            logger.error(f"Whitelist error: {e}")
            return web.Response(text="Error whitelisting user", status=500)
            
    async def remove_user(self, request):
        """Remove a user"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        telegram_id = int(request.match_info['telegram_id'])
        
        try:
            # Remove from group if bot is available
            if self.bot:
                try:
                    await self.bot.ban_chat_member(
                        chat_id=int(os.getenv("GROUP_ID", "-1002384609773")),
                        user_id=telegram_id
                    )
                except:
                    pass
                    
            # Update database
            self.db.cancel_subscription(telegram_id)
            raise web.HTTPFound('/users')
        except Exception as e:
            logger.error(f"Remove user error: {e}")
            return web.Response(text="Error removing user", status=500)
            
    async def extend_subscription(self, request):
        """Extend a user's subscription"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        telegram_id = int(request.match_info['telegram_id'])
        
        try:
            user = self.db.get_user(telegram_id)
            if user:
                # Extend by 30 days
                if user.next_payment_date:
                    new_date = user.next_payment_date + timedelta(days=30)
                else:
                    new_date = datetime.utcnow().date() + timedelta(days=30)
                    
                self.db.update_user(
                    telegram_id=telegram_id,
                    next_payment_date=new_date,
                    subscription_status='active'
                )
                
            raise web.HTTPFound('/users')
        except Exception as e:
            logger.error(f"Extend subscription error: {e}")
            return web.Response(text="Error extending subscription", status=500)
            
    async def stats_handler(self, request):
        """Show detailed statistics"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        # For now, redirect to dashboard
        # Could be expanded with more detailed stats
        raise web.HTTPFound('/dashboard')
        
    async def export_csv_handler(self, request):
        """Export users as CSV"""
        if not await self.check_auth(request):
            raise web.HTTPFound('/login')
            
        try:
            users = self.db.get_all_users()
            
            # Create CSV
            csv_lines = ["telegram_id,username,status,payment_method,next_payment_date,created_at"]
            for user in users:
                csv_lines.append(
                    f"{user.telegram_id},"
                    f"{user.username or ''},"
                    f"{user.subscription_status},"
                    f"{user.payment_method or ''},"
                    f"{user.next_payment_date or ''},"
                    f"{user.created_at}"
                )
                
            csv_content = '\n'.join(csv_lines)
            
            return web.Response(
                text=csv_content,
                headers={
                    'Content-Type': 'text/csv',
                    'Content-Disposition': f'attachment; filename="users_{datetime.now().strftime("%Y%m%d")}.csv"'
                }
            )
        except Exception as e:
            logger.error(f"Export error: {e}")
            return web.Response(text="Error exporting data", status=500)
            
def create_admin_app(db_client: SupabaseClient, bot=None):
    """Create the admin dashboard app"""
    dashboard = AdminDashboard(db_client, bot)
    return dashboard.app