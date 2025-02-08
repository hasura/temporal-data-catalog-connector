# Set the default target to 'build'
.DEFAULT_GOAL := build

# Use bash as the shell for executing commands
SHELL = /usr/bin/env bash

# Extract the version from the latest git tag
RELEASE_VERSION := $(shell git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")

# Define 'build' and 'clean' as phony targets (not associated with files)
.PHONY: build
.PHONY: clean

# The 'build' target depends on creating the connector-definition.tgz file
build: dist/connector-definition.tgz

# The 'clean' target removes the dist directory
clean:
	rm -rf dist

# Create the dist and dist/.hasura-connector directories
dist:
	mkdir -p dist
	mkdir -p dist/.hasura-connector

# Copy connector-metadata.yaml to dist/.hasura-connector
dist/.hasura-connector/connector-metadata.yaml: connector-metadata.yaml dist
	cp -f connector-metadata.yaml dist/.hasura-connector

# Copy Dockerfile to dist/.hasura-connector and replace the version
dist/.hasura-connector/Dockerfile: Dockerfile dist
	cp -f Dockerfile dist/.hasura-connector/
	sed -i 's/{{VERSION}}/$(subst v,,$(RELEASE_VERSION))/g' dist/.hasura-connector/Dockerfile
	# sed -i '' 's/{{VERSION}}/$(subst v,,$(RELEASE_VERSION))/g' dist/.hasura-connector/Dockerfile
	
# Copy .dockerignore to dist/.hasura-connector
dist/.hasura-connector/.dockerignore: .dockerignore dist
	cp -f .dockerignore dist/.hasura-connector/

# Find all files in the template directory
template_files := $(wildcard template/*)
# Create corresponding paths for template files in the dist directory
dist_template_files := $(patsubst template/%,dist/%,$(template_files))

# Copy all template files to the dist directory
$(dist_template_files): $(template_files)
	cp -f $(template_files) dist/

# Find all files in the scripts directory
script_files := $(wildcard scripts/*)
# Create corresponding paths for script files in dist/.hasura-connector
dist_script_files := $(patsubst scripts/%,dist/.hasura-connector/%,$(script_files))

# Copy all script files to dist/.hasura-connector
$(dist_script_files): $(script_files)
	cp -f $(script_files) dist/.hasura-connector/

# Create the final connector-definition.tgz file
dist/connector-definition.tgz: dist/.hasura-connector/connector-metadata.yaml dist/.hasura-connector/Dockerfile dist/.hasura-connector/.dockerignore $(dist_template_files) $(dist_script_files)
	shopt -s dotglob && cd dist && tar -czvf connector-definition.tgz *