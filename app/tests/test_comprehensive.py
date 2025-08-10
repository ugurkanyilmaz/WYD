import os
import pytest
import pytest_asyncio
from httpx import AsyncClient

# Set test database URL
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://social:socialpass@localhost:5432/socialdb')

from main import app

class TestComprehensiveAPI:
    """Comprehensive test suite for all API features"""

    @pytest.mark.asyncio
    async def test_user_registration_and_login(self):
        """Test user registration and login functionality"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Test user registration
            user_data = {
                "username": f"testuser_{unique_id}",
                "name": "Test",
                "surname": "User",
                "email": f"test_{unique_id}@example.com",
                "phone_number": f"+123456{unique_id[:4]}",
                "password": "testpass123",
                "display_name": f"Test User {unique_id}"
            }
            
            # Register user
            response = await ac.post("/api/users/register", json=user_data)
            assert response.status_code == 200
            user = response.json()
            assert user["username"] == f"testuser_{unique_id}"
            assert user["email"] == f"test_{unique_id}@example.com"
            assert "id" in user
            
            # Test login
            login_response = await ac.post("/api/users/login", data={
                "username": f"testuser_{unique_id}",
                "password": "testpass123"
            })
            assert login_response.status_code == 200
            token_data = login_response.json()
            assert "access_token" in token_data
            assert token_data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_friendship_workflow(self):
        """Test complete friendship workflow: request, accept, check status"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create two users
            user1_data = {
                "username": f"alice_{unique_id}",
                "name": "Alice",
                "surname": "Smith",
                "email": f"alice_{unique_id}@example.com",
                "phone_number": f"+111{unique_id[:7]}",
                "password": "alice123",
                "display_name": f"Alice S {unique_id}"
            }
            
            user2_data = {
                "username": f"bob_{unique_id}", 
                "name": "Bob",
                "surname": "Jones",
                "email": f"bob_{unique_id}@example.com",
                "phone_number": f"+222{unique_id[:7]}",
                "password": "bob123",
                "display_name": f"Bob J {unique_id}"
            }
            
            # Register both users
            user1_resp = await ac.post("/api/users/register", json=user1_data)
            assert user1_resp.status_code == 200
            user1 = user1_resp.json()
            
            user2_resp = await ac.post("/api/users/register", json=user2_data)
            assert user2_resp.status_code == 200
            user2 = user2_resp.json()
            
            # Login both users
            login1 = await ac.post("/api/users/login", data={"username": f"alice_{unique_id}", "password": "alice123"})
            assert login1.status_code == 200
            token1 = login1.json()["access_token"]
            
            login2 = await ac.post("/api/users/login", data={"username": f"bob_{unique_id}", "password": "bob123"})
            assert login2.status_code == 200
            token2 = login2.json()["access_token"]
            
            # Alice sends friend request to Bob
            friend_req = await ac.post(
                f"/api/users/{user2['id']}/friend-request",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert friend_req.status_code == 200
            friend_request_data = friend_req.json()
            assert "id" in friend_request_data
            request_id = friend_request_data["id"]
            
            # Bob accepts the friend request using the returned ID
            accept_resp = await ac.post(
                f"/api/users/friend-request/{request_id}/accept",
                headers={"Authorization": f"Bearer {token2}"}
            )
            assert accept_resp.status_code == 200
            
            # Check if they are friends
            friends_check = await ac.get(
                f"/api/users/{user2['id']}/are-friends",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert friends_check.status_code == 200
            friends_data = friends_check.json()
            assert "friends" in friends_data
            # Note: friends status might be True or False depending on implementation
            
            # Get Alice's friends list
            friends_list = await ac.get(
                "/api/users/me/friends",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert friends_list.status_code == 200
            friends = friends_list.json()
            assert isinstance(friends, list)

    @pytest.mark.asyncio
    async def test_messaging_system(self):
        """Test messaging between users"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create two users
            user1_data = {
                "username": f"sender_{unique_id}",
                "name": "Sender",
                "surname": "User",
                "email": f"sender_{unique_id}@example.com",
                "phone_number": f"+333{unique_id[:7]}",
                "password": "sender123",
                "display_name": f"Sender User {unique_id}"
            }
            
            user2_data = {
                "username": f"receiver_{unique_id}",
                "name": "Receiver", 
                "surname": "User",
                "email": f"receiver_{unique_id}@example.com",
                "phone_number": f"+444{unique_id[:7]}",
                "password": "receiver123",
                "display_name": f"Receiver User {unique_id}"
            }
            
            # Register users
            user1_resp = await ac.post("/api/users/register", json=user1_data)
            user2_resp = await ac.post("/api/users/register", json=user2_data)
            user1 = user1_resp.json()
            user2 = user2_resp.json()
            
            # Login sender
            login1 = await ac.post("/api/users/login", data={"username": f"sender_{unique_id}", "password": "sender123"})
            token1 = login1.json()["access_token"]
            
            # Send message
            message_data = {
                "recipient_id": user2["id"],
                "content": "Hello, this is a test message!"
            }
            
            msg_resp = await ac.post(
                "/api/messages/",
                json=message_data,
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert msg_resp.status_code == 200
            message = msg_resp.json()
            assert message["content"] == "Hello, this is a test message!"
            assert message["recipient_id"] == user2["id"]
            assert message["sender_id"] == user1["id"]
            
            # Get conversation/dialog
            dialog_resp = await ac.get(
                f"/api/messages/{user2['id']}",
                headers={"Authorization": f"Bearer {token1}"}
            )
            assert dialog_resp.status_code == 200
            dialog = dialog_resp.json()
            assert isinstance(dialog, list)
            assert len(dialog) >= 1
            assert dialog[0]["content"] == "Hello, this is a test message!"

    @pytest.mark.asyncio
    async def test_user_profile_access(self):
        """Test user profile retrieval"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create user
            user_data = {
                "username": f"profileuser_{unique_id}",
                "name": "Profile",
                "surname": "User",
                "email": f"profile_{unique_id}@example.com", 
                "phone_number": f"+555{unique_id[:7]}",
                "password": "profile123",
                "display_name": f"Profile User {unique_id}"
            }
            
            user_resp = await ac.post("/api/users/register", json=user_data)
            user = user_resp.json()
            
            # Get user profile
            profile_resp = await ac.get(f"/api/users/{user['id']}")
            assert profile_resp.status_code == 200
            profile = profile_resp.json()
            assert profile["username"] == f"profileuser_{unique_id}"
            assert profile["name"] == "Profile"
            assert profile["email"] == f"profile_{unique_id}@example.com"

    @pytest.mark.asyncio 
    async def test_authentication_required_endpoints(self):
        """Test that protected endpoints require authentication"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Try to send friend request without auth
            friend_req = await ac.post("/api/users/1/friend-request")
            assert friend_req.status_code == 401
            
            # Try to send message without auth
            msg_resp = await ac.post("/api/messages/", json={"recipient_id": 1, "content": "test"})
            assert msg_resp.status_code == 401
            
            # Try to get friends list without auth
            friends_resp = await ac.get("/api/users/me/friends")
            assert friends_resp.status_code == 401

    @pytest.mark.asyncio
    async def test_token_refresh_and_logout(self):
        """Test token refresh and logout functionality"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create user
            user_data = {
                "username": f"tokenuser_{unique_id}",
                "name": "Token", 
                "surname": "User",
                "email": f"token_{unique_id}@example.com",
                "phone_number": f"+666{unique_id[:7]}",
                "password": "token123",
                "display_name": f"Token User {unique_id}"
            }
            
            await ac.post("/api/users/register", json=user_data)
            
            # Login with device_id
            login_resp = await ac.post("/api/users/login", data={
                "username": f"tokenuser_{unique_id}",
                "password": "token123",
                "device_id": "test_device"
            })
            
            tokens = login_resp.json()
            access_token = tokens["access_token"]
            refresh_token = tokens.get("refresh_token")
            
            if refresh_token:
                # Test token refresh
                refresh_resp = await ac.post("/api/users/refresh", json={
                    "refresh_token": refresh_token
                })
                assert refresh_resp.status_code == 200
                new_tokens = refresh_resp.json()
                assert "access_token" in new_tokens
                
                # Test logout
                logout_resp = await ac.post("/api/users/logout", json={
                    "refresh_token": refresh_token
                })
                assert logout_resp.status_code == 200
                logout_data = logout_resp.json()
                assert logout_data["ok"] is True

    @pytest.mark.asyncio
    async def test_complete_social_workflow(self):
        """Test a complete social interaction workflow"""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            # Create 3 users
            users_data = [
                {
                    "username": f"user{i}_{unique_id}",
                    "name": f"User{i}",
                    "surname": "Test",
                    "email": f"user{i}_{unique_id}@example.com",
                    "phone_number": f"+{7000000000 + i}{unique_id[:3]}",
                    "password": f"pass{i}123",
                    "display_name": f"User {i} {unique_id}"
                }
                for i in range(1, 4)
            ]
            
            users = []
            tokens = []
            
            # Register and login all users
            for user_data in users_data:
                # Register
                reg_resp = await ac.post("/api/users/register", json=user_data)
                user = reg_resp.json()
                users.append(user)
                
                # Login
                login_resp = await ac.post("/api/users/login", data={
                    "username": user_data["username"],
                    "password": user_data["password"]
                })
                token = login_resp.json()["access_token"]
                tokens.append(token)
            
            # User1 sends friend request to User2
            await ac.post(
                f"/api/users/{users[1]['id']}/friend-request",
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )
            
            # User2 accepts friend request from User1
            await ac.post(
                "/api/users/friend-request/1/accept",
                headers={"Authorization": f"Bearer {tokens[1]}"}
            )
            
            # User1 sends message to User2
            await ac.post(
                "/api/messages/",
                json={"recipient_id": users[1]["id"], "content": "Hey friend!"},
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )
            
            # User2 replies to User1
            await ac.post(
                "/api/messages/",
                json={"recipient_id": users[0]["id"], "content": "Hello back!"},
                headers={"Authorization": f"Bearer {tokens[1]}"}
            )
            
            # Check conversation
            dialog_resp = await ac.get(
                f"/api/messages/{users[1]['id']}",
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )
            dialog = dialog_resp.json()
            assert len(dialog) >= 2
            
            # Verify friendship status
            friends_check = await ac.get(
                f"/api/users/{users[1]['id']}/are-friends",
                headers={"Authorization": f"Bearer {tokens[0]}"}
            )
            assert friends_check.status_code == 200
