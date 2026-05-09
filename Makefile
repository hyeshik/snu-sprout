PYTHON ?= python3
FONTFORGE ?= fontforge
SOURCE_ZIP_URL ?= https://seed.line.me/src/images/fonts/LINE_Seed_Sans_KR.zip
DOWNLOAD_DIR ?= vendor/downloads
SOURCE_DIR ?= original
OUTPUT_DIR ?= instance_otf
BUILD_FLAGS ?=
PACKAGE_NAME ?= SNUSproutSans
PACKAGE_ZIP ?= dist/$(PACKAGE_NAME).zip

.PHONY: build test package clean

build:
	rm -f "$(OUTPUT_DIR)"/SNUSproutSans-*.otf
	$(FONTFORGE) -lang=py -script build_snu_sprout_sans.py \
		--source-zip-url "$(SOURCE_ZIP_URL)" \
		--download-dir "$(DOWNLOAD_DIR)" \
		--source-dir "$(SOURCE_DIR)" \
		--output-dir "$(OUTPUT_DIR)" \
		$(BUILD_FLAGS)

test:
	$(PYTHON) -m unittest discover -s tests

package: build
	$(PYTHON) make_distribution_zip.py \
		--input-dir "$(OUTPUT_DIR)" \
		--zip-name "$(PACKAGE_NAME).zip" \
		--include-readme
	test -f "$(PACKAGE_ZIP)"

clean:
	rm -rf instance_otf original vendor dist test-build
