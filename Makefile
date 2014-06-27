PREFIX=/usr/local
PYTHON2=python2.7
PYTHON3=python3

all:
	@echo "Usage: $(MAKE) install"
	@echo "Usage: $(MAKE) test"
	@echo "Usage: $(MAKE) doc"
	@echo "Usage: $(MAKE) clean"

install:
	$(PYTHON2) ./setup.py -v install --force --prefix=$(PREFIX)
	$(PYTHON3) ./setup.py -v install --force --prefix=$(PREFIX)
	cp -rv tklpatch $(PREFIX)/share/
	cp examples/* $(PREFIX)/share/
	install -d $(PREFIX)/share/man/man1
	cp man/*.1 $(PREFIX)/share/man/man1

test:
	$(PYTHON2) -m unittest -v -v outscale_image_factory.test

doc:
	ronn man/*.ronn

clean:
	rm -rf build dist *.egg-info

.PHONY: all install test doc clean
