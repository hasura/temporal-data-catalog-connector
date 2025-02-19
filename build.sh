rm -rf dist

poetry version patch

# Possibly commit the change to version control and tag it
git add pyproject.toml
git commit -m "Bump version"
git tag $(poetry version -s)

poetry build
