import re
import sys
import json


class Operator:
    """Base class for all Operator plugins.

    Note: This is an abstract class. You must extend ``__init__`` and call
    ``super`` to ensure this class's constructor is called. You must override
    ``handle_artifact`` with the same signature. You may define additional
    ``handle_{artifact_type}`` methods as needed (see the threatkb operator for
    an example) - these methods are purely convention, and are not required.

    When adding additional methods to child classes, consider prefixing the
    method name with an underscore to denote a ``_private_method``. Do not
    override other existing methods from this class.
    """
    def __init__(self, logger, elasticsearch, allowed_sources=None):
        """Override this constructor in child classes.

        The arguments above (artifact_types, filter_string, allowed_sources)
        should be accepted explicity as above, in all child classes.

        Additional arguments should be added: url, auth, etc, whatever is
        needed to set up the object.

        Each operator should default self.artifact_types to a list of Artifacts
        supported by the plugin, and allow passing in artifact_types to
        overwrite that default.

        Example:

        >>> self.artifact_types = artifact_types or [
        ...     artifacts.IPAddress,
        ...     artifacts.Domain,
        ... ]

        It's recommended to call this __init__ method via super from all child
        classes. Remember to do so *before* setting any default artifact_types.
        """
        self.logger = logger
        self.blacklist = re.compile('|'.join([re.escape(word) for word in allowed_sources]), re.IGNORECASE)
        self.es = elasticsearch

    def response(self, content, onion, operator_name):
        """
        status: success/failure
        content: dict
        onion: str
        return: dict
        """
        try:
            return {operator_name: json.loads(str(content)), 'hiddenService': onion}
        except json.decoder.JSONDecodeError as e:
            self.logger.info('JosnDecode Error')
            return {operator_name: content, 'hiddenService': onion}
        #except TypeError:
        #    return {operator_name: None, 'hiddenService': onion}
        except Exception as e:
            self.logger.error(e)

    def handle_onion(self, url):
        """Override with the same signature.

        :param artifact: A single ``Artifact`` object.
        :returns: None (always ignored)
        """
        raise NotImplementedError()


    def _onion_is_allowed(self, response, type='URL'):
        """Returns True if this is allowed by this plugin's filters."""
        # Must be in allowed_sources, if set.
        if type == 'URL':
            print(response)
            blacklist = self.blacklist.findall(response['hiddenService'])
        elif type == 'HTML':
            response['simple-html'].pop('status')
            response['simple-html']['status'] = 'blocked'
            blacklist = self.blacklist.findall(response['simple-html']['HTML'])
        if blacklist:
            self.es.save(response)
            return False
        return True


    def process(self, onions):
        """Process all applicable onions."""
        for onion in onions:
            if self._onion_is_allowed(
                    self.response({'status':'blocked'},onion.url,'regex-blacklist'),
                    type='URL'):
                self.handle_onion(onion.url)

