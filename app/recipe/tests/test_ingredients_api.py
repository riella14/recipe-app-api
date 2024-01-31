"""
Tests for the ingredients API.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(ingredient_id):
    """Create and return an ingredient detail url."""
    return reverse('recipe:ingredient-detail', args=[ingredient_id])


def create_user(email='user@example.com', password='testpass123'):
    """"Create and return user."""
    return get_user_model().objects.create_user(email, password)


class PublicIngredientsApiTests(TestCase):
    """"Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving ingredients."""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """"Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """Test retrieving a list of ingredients"""
        kale = {'name': 'Kale', 'quantity': '10', 'unit': 'ounces'}
        vanilla = {'name': 'Vanilla', 'quantity': '1', 'unit': 'tablespoon'}
        Ingredient.objects.create(user=self.user, **kale)
        Ingredient.objects.create(user=self.user, **vanilla)

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test list of ingredients is limited to authenticated user."""
        user2 = create_user(email='user2@example.com')
        salt = {'name': 'Salt', 'quantity': '', 'unit': ''}
        pepper = {'name': 'Pepper', 'quantity': '', 'unit': ''}
        Ingredient.objects.create(user=user2, **salt)
        ingredient = Ingredient.objects.create(user=self.user, **pepper)

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)
        self.assertEqual(res.data[0]['quantity'], ingredient.quantity)
        self.assertEqual(res.data[0]['unit'], ingredient.unit)
        self.assertEqual(res.data[0]['id'], ingredient.id)

    def test_partial_update_ingredient(self):
        """Test updating an ingredient partially."""
        name = 'Cilantro'
        unit = 'leaves'
        ingredient = Ingredient.objects.create(user=self.user, **{
            'name': name,
            'quantity': '2',
            'unit': unit})

        payload = {'quantity': '3'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.quantity, payload['quantity'])
        self.assertEqual(ingredient.name, name)
        self.assertEqual(ingredient.unit, unit)
        self.assertEqual(ingredient.user, self.user)

    def test_full_update_ingredient(self):
        """Test updating an ingredient partially."""
        ingredient = Ingredient.objects.create(user=self.user, **{
            'name': 'Cilantro',
            'quantity': '2',
            'unit': 'leaves'})

        payload = {'name': 'Basil', 'quantity': '5', 'unit': 'ounces'}
        url = detail_url(ingredient.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(ingredient, k), v)
        self.assertEqual(ingredient.user, self.user)

    def test_delete_ingredient(self):
        """Test deleting an ingredient."""
        ingredient =  Ingredient.objects.create(user=self.user, **{
            'name': 'Lettuce',
            'quantity': '14',
            'unit': 'grams'})

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())
