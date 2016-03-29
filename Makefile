.PHONY: release

release:
ifeq ($(VERSION),)
	$(error VERSION must be set to build a release and deploy this package)
endif
ifeq ($(RELEASE_GPG_KEYNAME),)
	$(error RELEASE_GPG_KEYNAME must be set to build a release and deploy this package)
endif
	@echo "==> Python (sdist release)"
	@python setup.py sdist upload -s -i $(RELEASE_GPG_KEYNAME)
	@bash ./publish $(VERSION)
