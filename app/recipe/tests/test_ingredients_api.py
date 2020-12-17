from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core import models

from recipe import serializers


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):
    """Test the publicly available Ingredients API"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required for retrieving ingredients"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test the authorized user Ingredients API"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@user.com',
            password='testpassword',
            name='Test User'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredient_list(self):
        """Test retrieving Ingredients"""
        models.Ingredient.objects.create(
            user=self.user,
            name='Carrot'
        )
        models.Ingredient.objects.create(
            user=self.user,
            name='Cucumber'
        )

        res = self.client.get(INGREDIENTS_URL)

        ingredients = models.Ingredient.objects.all().order_by('-name')
        serializer = serializers.IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Test that ingredients are returned only for given user"""
        user2 = get_user_model().objects.create_user(
            email='other_test@user.com',
            password='testpassword',
            name='Test User'
        )
        models.Ingredient.objects.create(
            user=user2,
            name='Milk'
        )
        ingredient = models.Ingredient.objects.create(
            user=self.user,
            name='Cheese'
        )

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        """Test creating a new ingredient"""
        payload = {
            'name': 'Test ingredient'
        }
        self.client.post(INGREDIENTS_URL, payload)

        exists = models.Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Test creating a ingredient with invalid payload"""
        payload = {
            'name': ''
        }
        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test filtering ingredients by those assigned to recipes"""
        ingredient1 = models.Ingredient.objects.create(
            user=self.user,
            name='Eggs'
        )
        ingredient2 = models.Ingredient.objects.create(
            user=self.user,
            name='Chicken'
        )
        recipe = models.Recipe.objects.create(
            title='Coriander eggs on toast',
            time_minutes=15,
            price=55.00,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = serializers.IngredientSerializer(ingredient1)
        serializer2 = serializers.IngredientSerializer(ingredient2)
        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_ingredients_assigned_unique(self):
        """Test filtering ingredients by assigned returns unique value"""
        ingredient = models.Ingredient.objects.create(
            user=self.user,
            name='Toast'
        )
        models.Ingredient.objects.create(
            user=self.user,
            name='Turkey'
        )
        recipe1 = models.Recipe.objects.create(
            title='Coriander eggs on toast',
            time_minutes=15,
            price=55.00,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)

        recipe2 = models.Recipe.objects.create(
            title='Avocado on toast',
            time_minutes=25,
            price=15.00,
            user=self.user
        )
        recipe2.ingredients.add(ingredient)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
