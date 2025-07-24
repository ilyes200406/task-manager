import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Note

# -------------------------------------------------------------------
# FIXTURES (Reusable setup code for tests)
# -------------------------------------------------------------------

@pytest.fixture
def client():
    """
    Returns a DRF APIClient object.
    APIClient lets us simulate HTTP requests (GET, POST, etc.) to our API.
    """
    return APIClient()


@pytest.fixture
def create_user(db):
    """
    Creates and returns a test user.
    - 'db' is a special pytest marker that gives this fixture access to the test database.
    """
    user = User.objects.create_user(username='ilyes', password='mypassword')
    return user


@pytest.fixture
def auth_client(create_user):
    """
    Returns an APIClient authenticated as 'create_user'.
    - We use 'force_authenticate' to skip the login process.
    - This is needed because our views require IsAuthenticated.
    """
    client = APIClient()
    client.force_authenticate(user=create_user)  # Pretend this user is logged in
    return client


@pytest.fixture
def create_note(create_user):
    """
    Creates and returns a sample Note for the test user.
    """
    return Note.objects.create(title="Test Note", content="Some content", author=create_user)


# -------------------------------------------------------------------
# TESTS FOR USER REGISTRATION
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_user_registration(client):
    """
    Test that POST /register/ successfully creates a new user.
    """
    url = reverse('create-user')  # Find the URL for the 'create-user' endpoint
    data = {'username': 'ilyes2', 'password': 'mypassword'}

    # Send a POST request to create a new user
    response = client.post(url, data, format='json')

    # Check if the user was created successfully
    assert response.status_code == 201  # 201 Created
    assert User.objects.filter(username='ilyes2').exists()  # Verify user exists in DB


# -------------------------------------------------------------------
# TESTS FOR NOTES (LIST, CREATE, DELETE)
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_list_notes(auth_client, create_note):
    """
    Test GET /notes/
    - The authenticated user should see their own notes.
    """
    url = reverse('note-list')  # URL for listing notes
    response = auth_client.get(url, format='json')

    assert response.status_code == 200  # 200 OK
    assert len(response.data) == 1      # One note is returned
    assert response.data[0]['title'] == "Test Note"  # The title matches


@pytest.mark.django_db
def test_create_note(auth_client):
    """
    Test POST /notes/
    - The authenticated user can create a new note.
    """
    url = reverse('note-list')
    data = {'title': 'New Note', 'content': 'Some content'}

    # Send POST request with data
    response = auth_client.post(url, data, format='json')

    assert response.status_code == 201  # 201 Created
    assert Note.objects.count() == 1    # One note exists in DB
    assert Note.objects.first().title == 'New Note'


@pytest.mark.django_db
def test_delete_note(auth_client, create_note):
    """
    Test DELETE /notes/delete/<id>/
    - The authenticated user can delete their own note.
    """
    url = reverse('delete-note', args=[create_note.id])
    response = auth_client.delete(url)

    assert response.status_code == 204  # 204 No Content
    assert Note.objects.count() == 0    # No notes remain


@pytest.mark.django_db
def test_cannot_delete_other_users_note(auth_client):
    """
    Test that a user cannot delete another user's note.
    """
    # Create another user and their note
    other_user = User.objects.create_user(username='john', password='johnpassword')
    note = Note.objects.create(title="Other's Note", content="Secret", author=other_user)

    # Try to delete the other user's note
    url = reverse('delete-note', args=[note.id])
    response = auth_client.delete(url)

    assert response.status_code == 404  # 404 Not Found (note not visible to this user)
    assert Note.objects.count() == 1    # Note still exists
