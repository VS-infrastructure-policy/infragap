import json
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class Report:
    """Holds network-level connectivity metrics."""

    def __init__(self, metrics, segments):
        self._metrics = metrics
        self.segments = segments
        self.total_length_km = metrics["total_length_km"]
        self.components = metrics["num_components"]
        self.lcc_length_km = metrics["lcc_length_km"]
        self.lcc_ratio = metrics["lcc_ratio"]
        self.stranded_pct = metrics["stranded_pct"]
        self.avg_component_length_m = metrics["avg_component_length_m"]
        self.beta = metrics["beta"]
        self.alpha = metrics["alpha"]
        self.gamma = metrics["gamma"]
        self.bridges = metrics["bridges"]
        self.edge_connectivity = metrics["edge_connectivity"]

    def __str__(self):
        return (
            f"\n  Network Diagnosis\n"
            f"  {'-' * 35}\n"
            f"  Total length       {self.total_length_km:>8} km\n"
            f"  Segments           {self.segments:>8,}\n"
            f"  Components         {self.components:>8,}\n"
            f"  Avg component      {self.avg_component_length_m:>8.0f} m\n"
            f"\n"
            f"  Connectivity\n"
            f"    LCC length       {self.lcc_length_km:>8} km\n"
            f"    LCC ratio        {self.lcc_ratio * 100:>7.1f}%\n"
            f"    Stranded         {self.stranded_pct:>7.1f}%\n"
            f"    Beta (e/v)       {self.beta:>8}\n"
            f"    Alpha            {self.alpha:>8}\n"
            f"    Gamma            {self.gamma:>8}\n"
            f"\n"
            f"  Resilience\n"
            f"    Bridges          {self.bridges:>8}\n"
            f"    Edge connectivity{self.edge_connectivity:>8}\n"
        )

    def to_dict(self):
        result = dict(self._metrics)
        result["segments"] = self.segments
        result.pop("bridge_list", None)
        result.pop("component_lengths_m", None)
        return result

    def to_dataframe(self):
        return pd.DataFrame([self.to_dict()])

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)


class ZoneReport:
    """Holds per-zone metrics as a pandas DataFrame."""

    def __init__(self, df):
        self.df = df
        self._geometries = {}

    def __str__(self):
        return self.df.to_string(index=False)

    def __repr__(self):
        return self.df.to_string(index=False)

    def to_excel(self, path):
        self.df.to_excel(path, index=False)
        logger.info("Saved to %s", path)

    def to_geojson(self, path):
        features = []
        for _, row in self.df.iterrows():
            zone_name = row.iloc[0]

            props = {}
            for col in self.df.columns:
                val = row[col]
                if hasattr(val, "item"):
                    val = val.item()
                props[col] = val

            geom = self._geometries.get(zone_name)
            if geom:
                feature = {
                    "type": "Feature",
                    "properties": props,
                    "geometry": geom.__geo_interface__,
                }
                features.append(feature)

        collection = {"type": "FeatureCollection", "features": features}
        with open(path, "w") as f:
            json.dump(collection, f)
        logger.info("Saved to %s", path)
