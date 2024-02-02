"""
Tests for the ingredients API.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Ingredient,
    Recipe,
)

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
        ingredient = Ingredient.objects.create(user=self.user, **{
            'name': 'Lettuce',
            'quantity': '14',
            'unit': 'grams'})

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name='Macaroni', quantity='2', unit='cups')
        in2 = Ingredient.objects.create(user=self.user, name='Evaporated Milk',
                                        quantity='1', unit='can')
        recipe = Recipe.objects.create(
            title='Sopas',
            time_minutes=45,
            price=Decimal('2.34'),
            user=self.user,
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ing = Ingredient.objects.create(user=self.user, name='Eggs', quantity='2', unit='whole')
        Ingredient.objects.create(user=self.user, name='Lime', quantity='5', unit='pieces')
        recipe1 = Recipe.objects.create(
            title='Egg Drop Soup',
            time_minutes=17,
            price=Decimal('2.14'),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title='Eggs Benedict',
            time_minutes=12,
            price=Decimal('1.88'),
            user=self.user,
        )
        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
