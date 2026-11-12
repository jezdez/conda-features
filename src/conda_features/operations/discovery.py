"""Load feature declarations through the dedicated Pluggy interface."""

from importlib.metadata import entry_points

from conda import CondaError
from pluggy import PluginManager

from ..hooks import FeatureSpecs
from ..models import Catalog, Feature


def discover() -> Catalog:
    manager = PluginManager("conda_features")
    manager.add_hookspecs(FeatureSpecs)
    features = {}
    for entry in entry_points(group="conda_features"):
        try:
            provider = entry.load()
            manager.register(provider, name=entry.name)
            manager.check_pending()
        except Exception as exc:
            raise CondaError(f"Cannot load feature provider {entry.name!r}.") from exc
        if not any(
            impl.plugin is provider
            for impl in manager.hook.conda_features.get_hookimpls()
        ):
            raise CondaError(
                f"Provider {entry.name!r} must declare conda_features with conda_features.hooks.hookimpl."
            )
        hook = manager.subset_hook_caller(
            "conda_features", remove_plugins=manager.get_plugins() - {provider}
        )
        try:
            declarations = [feature for result in hook() for feature in result]
        except Exception as exc:
            raise CondaError(
                f"Cannot collect features from provider {entry.name!r}."
            ) from exc
        for feature in declarations:
            if not isinstance(feature, Feature):
                raise CondaError(f"Invalid feature declaration from {entry.name!r}.")
            if feature.name in features:
                raise CondaError(f"Duplicate feature ID: {feature.name}")
            features[feature.name] = (entry.name, feature)
    return dict(sorted(features.items()))
