.PHONY: release release_bdist_egg

release: release_bdist_egg
ifeq ($(RELEASE_GPG_KEYNAME),)
	$(error RELEASE_GPG_KEYNAME must be set to build a release and deploy this package)
else
	@echo "==> Python (sdist release)"
	@python setup.py sdist upload -s -i $(RELEASE_GPG_KEYNAME)
endif

release_bdist_egg:
ifeq ($(RELEASE_GPG_KEYNAME),)
	$(error RELEASE_GPG_KEYNAME must be set to build a release and deploy this package)
else
	@python2.7 --version
	@python3.3 --version
	@python3.4 --version
	@python3.5 --version
	@echo "==> Python 2.7 (release)"
	@python2.7 setup.py build --build-base=py-build/2.7 bdist_egg upload -s -i $(RELEASE_GPG_KEYNAME)
	@echo "==> Python 3.3 (release)"
	@python3.3 setup.py build --build-base=py-build/3.3 bdist_egg upload -s -i $(RELEASE_GPG_KEYNAME)
	@echo "==> Python 3.4 (release)"
	@python3.4 setup.py build --build-base=py-build/3.4 bdist_egg upload -s -i $(RELEASE_GPG_KEYNAME)
	@echo "==> Python 3.5 (release)"
	@python3.5 setup.py build --build-base=py-build/3.5 bdist_egg upload -s -i $(RELEASE_GPG_KEYNAME)
endif
