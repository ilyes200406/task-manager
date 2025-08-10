# api_tests.py
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from api.models import Note
from rest_framework.exceptions import NotFound

# -------------------------------------------------------------------
# FIXTURES (Mocked setup for tests)
# -------------------------------------------------------------------

@pytest.fixture
def client():
    """Returns a DRF APIClient object."""
    return APIClient()

@pytest.fixture
def mock_user(mocker):
    """Returns a mock User object."""
    user = mocker.MagicMock(spec=User)
    user.username = 'ilyes'
    user.id = 1
    return user

@pytest.fixture
def mock_note(mocker, mock_user):
    """Returns a mock Note object."""
    note = mocker.MagicMock(spec=Note)
    note.id = 1
    note.title = "Test Note"
    note.content = "Some content"
    note.author = mock_user
    return note

@pytest.fixture
def auth_client(mocker, mock_user):
    """Returns an authenticated APIClient with a mock user."""
    client = APIClient()
    client.force_authenticate(user=mock_user)
    return client

# -------------------------------------------------------------------
# TESTS FOR USER REGISTRATION
# -------------------------------------------------------------------

def test_user_registration(client, mocker):
    """
    Test that POST /register/ successfully creates a new user.
    """
    url = reverse('create-user')
    data = {'username': 'ilyes2', 'password': 'mypassword'}
    
    # Mock User.objects.create_user
    mock_create = mocker.patch('django.contrib.auth.models.User.objects.create_user')
    mock_create.return_value = User(username='ilyes2', id=1)
    
    response = client.post(url, data, format='json')
    
    assert response.status_code == 201
    mock_create.assert_called_once_with(username='ilyes2', password='mypassword')

# -------------------------------------------------------------------
# TESTS FOR NOTES (LIST, CREATE, DELETE)
# -------------------------------------------------------------------

def test_list_notes(auth_client, mocker, mock_user, mock_note):
    """
    Test GET /notes/
    """
    url = reverse('note-list')
    
    # Mock Note.objects.filter to return a queryset with our mock note
    mock_queryset = mocker.MagicMock()
    mock_queryset.__iter__.return_value = [mock_note]
    mocker.patch(
        'api.models.Note.objects.filter',
        return_value=mock_queryset
    )
    
    response = auth_client.get(url, format='json')
    
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['title'] == "Test Note"
    Note.objects.filter.assert_called_once_with(author=mock_user)

def test_create_note(auth_client, mocker, mock_user):
    """
    Test POST /notes/
    """
    url = reverse('note-list')
    data = {'title': 'New Note', 'content': 'Some content'}
    
    # Mock Note serializer and save
    mock_serializer = mocker.patch('api.serializers.NoteSerializer')
    mock_serializer_instance = mock_serializer.return_value
    mock_serializer_instance.is_valid.return_value = True
    mock_serializer_instance.save.return_value = None
    mock_serializer_instance.data = {'id': 1, 'title': 'New Note', 'content': 'Some content'}
    
    response = auth_client.post(url, data, format='json')
    
    assert response.status_code == 201
    mock_serializer_instance.save.assert_called_once_with(author=mock_user)
    mock_serializer.assert_called_once_with(data=data)

def test_create_note_invalid(auth_client, mocker, mock_user):
    """
    Test POST /notes/ with invalid data
    """
    url = reverse('note-list')
    data = {'title': '', 'content': 'Some content'}  # Invalid - empty title
    
    # Mock serializer to return invalid
    mock_serializer = mocker.patch('api.serializers.NoteSerializer')
    mock_serializer_instance = mock_serializer.return_value
    mock_serializer_instance.is_valid.return_value = False
    mock_serializer_instance.errors = {'title': ['This field may not be blank.']}
    
    response = auth_client.post(url, data, format='json')
    
    assert response.status_code == 400
    mock_serializer.assert_called_once_with(data=data)

def test_delete_note(auth_client, mocker, mock_user, mock_note):
    """
    Test DELETE /notes/delete/<id>/
    """
    url = reverse('delete-note', args=[mock_note.id])
    
    # Mock get_queryset to return our mock note
    mock_queryset = mocker.MagicMock()
    mock_queryset.filter.return_value.first.return_value = mock_note
    mocker.patch(
        'api.views.NoteDelete.get_queryset',
        return_value=mock_queryset
    )
    
    # Mock note deletion
    mock_delete = mocker.patch.object(mock_note, 'delete')
    
    response = auth_client.delete(url)
    
    assert response.status_code == 204
    mock_delete.assert_called_once()

def test_cannot_delete_other_users_note(auth_client, mocker, mock_user):
    """
    Test that a user cannot delete another user's note.
    """
    url = reverse('delete-note', args=[2])  # Note ID that doesn't belong to user
    
    # Mock get_queryset to return empty queryset
    mock_queryset = mocker.MagicMock()
    mock_queryset.filter.return_value.first.return_value = None
    mocker.patch(
        'api.views.NoteDelete.get_queryset',
        return_value=mock_queryset
    )
    
    response = auth_client.delete(url)
    
    assert response.status_code == 404
    mock_queryset.filter.assert_called_once_with(id=2)