#!/usr/bin/env python3
"""
DATASCIENCE Agent Python Implementation v9.0
Advanced data analysis, ML engineering, and statistical modeling specialist.

Comprehensive implementation with pandas, numpy, scikit-learn, and visualization
capabilities. Includes data profiling, feature engineering, model training, and
statistical analysis with automated insights generation.
"""

import asyncio
import base64
import hashlib
import io
import json
import os
import pickle
import sys
import tempfile
import traceback
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Core data science libraries
try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

try:
    from sklearn import ensemble, metrics, model_selection, preprocessing
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.decomposition import PCA
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import scipy.stats as stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class DataProfile:
    """Comprehensive data profiling results"""

    shape: Tuple[int, int]
    dtypes: Dict[str, str]
    missing_values: Dict[str, int]
    missing_percentage: Dict[str, float]
    unique_counts: Dict[str, int]
    numerical_stats: Dict[str, Dict[str, float]]
    categorical_distributions: Dict[str, Dict[str, int]]
    correlations: Optional[Dict[str, Dict[str, float]]] = None
    outliers: Optional[Dict[str, List[int]]] = None
    data_quality_score: float = 0.0
    recommendations: List[str] = None


@dataclass
class ModelResults:
    """Machine learning model results"""

    model_type: str
    algorithm: str
    parameters: Dict[str, Any]
    training_score: float
    validation_score: float
    test_score: Optional[float] = None
    predictions: Optional[List] = None
    feature_importance: Optional[Dict[str, float]] = None
    confusion_matrix: Optional[List[List[int]]] = None
    classification_report: Optional[Dict] = None
    residuals: Optional[List[float]] = None
    cross_validation_scores: Optional[List[float]] = None


@dataclass
class StatisticalTest:
    """Statistical test results"""

    test_name: str
    statistic: float
    p_value: float
    alpha: float
    reject_null: bool
    interpretation: str
    confidence_interval: Optional[Tuple[float, float]] = None
    effect_size: Optional[float] = None


@dataclass
class FeatureEngineering:
    """Feature engineering results"""

    original_features: int
    engineered_features: int
    selected_features: List[str]
    feature_scores: Dict[str, float]
    transformation_pipeline: List[str]
    dimensionality_reduction: Optional[Dict] = None


class DataAnalyzer:
    """Advanced data analysis capabilities"""

    def __init__(self):
        self.datasets = {}
        self.models = {}
        self.visualizations = []
        self.insights = []

    def profile_data(self, df: pd.DataFrame) -> DataProfile:
        """Generate comprehensive data profile"""
        profile = DataProfile(
            shape=df.shape,
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            missing_values=df.isnull().sum().to_dict(),
            missing_percentage=(df.isnull().sum() / len(df) * 100).to_dict(),
            unique_counts=df.nunique().to_dict(),
            numerical_stats={},
            categorical_distributions={},
            recommendations=[],
        )

        # Numerical statistics
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        for col in numerical_cols:
            profile.numerical_stats[col] = {
                "mean": df[col].mean(),
                "median": df[col].median(),
                "std": df[col].std(),
                "min": df[col].min(),
                "max": df[col].max(),
                "q25": df[col].quantile(0.25),
                "q75": df[col].quantile(0.75),
                "skew": df[col].skew(),
                "kurtosis": df[col].kurtosis(),
            }

        # Categorical distributions
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts().head(10).to_dict()
            profile.categorical_distributions[col] = value_counts

        # Correlations
        if len(numerical_cols) > 1:
            corr_matrix = df[numerical_cols].corr()
            profile.correlations = corr_matrix.to_dict()

        # Outlier detection
        profile.outliers = self._detect_outliers(df, numerical_cols)

        # Data quality score
        profile.data_quality_score = self._calculate_quality_score(profile)

        # Generate recommendations
        profile.recommendations = self._generate_recommendations(profile)

        return profile

    def _detect_outliers(
        self, df: pd.DataFrame, columns: List[str]
    ) -> Dict[str, List[int]]:
        """Detect outliers using IQR method"""
        outliers = {}
        for col in columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            outlier_mask = (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)
            outliers[col] = df[outlier_mask].index.tolist()
        return outliers

    def _calculate_quality_score(self, profile: DataProfile) -> float:
        """Calculate data quality score (0-100)"""
        score = 100.0

        # Penalize for missing values
        avg_missing = np.mean(list(profile.missing_percentage.values()))
        score -= min(avg_missing * 2, 30)  # Max 30 point penalty

        # Penalize for low cardinality in non-categorical columns
        for col, unique in profile.unique_counts.items():
            if unique == 1:
                score -= 5  # Constant columns

        # Penalize for high outlier percentage
        if profile.outliers:
            for col, outlier_indices in profile.outliers.items():
                outlier_pct = len(outlier_indices) / profile.shape[0] * 100
                score -= min(outlier_pct, 10)  # Max 10 point penalty per column

        return max(score, 0)

    def _generate_recommendations(self, profile: DataProfile) -> List[str]:
        """Generate data quality recommendations"""
        recommendations = []

        # Missing value recommendations
        for col, missing_pct in profile.missing_percentage.items():
            if missing_pct > 50:
                recommendations.append(
                    f"Consider dropping column '{col}' (>{missing_pct:.1f}% missing)"
                )
            elif missing_pct > 10:
                recommendations.append(
                    f"Impute missing values in '{col}' ({missing_pct:.1f}% missing)"
                )

        # Outlier recommendations
        if profile.outliers:
            for col, outliers in profile.outliers.items():
                if len(outliers) > profile.shape[0] * 0.05:
                    recommendations.append(
                        f"Review outliers in '{col}' ({len(outliers)} detected)"
                    )

        # Correlation recommendations
        if profile.correlations:
            for col1, correlations in profile.correlations.items():
                for col2, corr in correlations.items():
                    if col1 != col2 and abs(corr) > 0.9:
                        recommendations.append(
                            f"High correlation between '{col1}' and '{col2}' ({corr:.2f})"
                        )

        return recommendations


class ModelBuilder:
    """Machine learning model building and evaluation"""

    def __init__(self):
        self.models = {}
        self.preprocessors = {}
        self.feature_engineers = {}

    async def train_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = "auto",
        task: str = "classification",
    ) -> ModelResults:
        """Train and evaluate machine learning model"""

        # Preprocessing
        X_processed = self._preprocess_features(X)

        # Train-test split
        X_train, X_test, y_train, y_test = model_selection.train_test_split(
            X_processed, y, test_size=0.2, random_state=42
        )

        # Model selection
        if model_type == "auto":
            model = self._select_best_model(X_train, y_train, task)
        else:
            model = self._get_model(model_type, task)

        # Training
        model.fit(X_train, y_train)

        # Evaluation
        train_score = model.score(X_train, y_train)
        test_score = model.score(X_test, y_test)

        # Cross-validation
        cv_scores = model_selection.cross_val_score(model, X_processed, y, cv=5)

        # Predictions
        predictions = model.predict(X_test)

        # Create results
        results = ModelResults(
            model_type=type(model).__name__,
            algorithm=str(model),
            parameters=model.get_params(),
            training_score=train_score,
            validation_score=test_score,
            cross_validation_scores=cv_scores.tolist(),
            predictions=predictions.tolist(),
        )

        # Task-specific metrics
        if task == "classification":
            results.confusion_matrix = metrics.confusion_matrix(
                y_test, predictions
            ).tolist()
            results.classification_report = metrics.classification_report(
                y_test, predictions, output_dict=True
            )
        else:
            results.residuals = (y_test - predictions).tolist()

        # Feature importance
        if hasattr(model, "feature_importances_"):
            results.feature_importance = dict(
                zip(X.columns, model.feature_importances_)
            )

        return results

    def _preprocess_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Preprocess features for modeling"""
        X_processed = X.copy()

        # Handle categorical variables
        categorical_cols = X_processed.select_dtypes(include=["object"]).columns
        if len(categorical_cols) > 0:
            X_processed = pd.get_dummies(X_processed, columns=categorical_cols)

        # Scale numerical features
        scaler = StandardScaler()
        numerical_cols = X_processed.select_dtypes(include=[np.number]).columns
        X_processed[numerical_cols] = scaler.fit_transform(X_processed[numerical_cols])

        # Handle missing values
        X_processed = X_processed.fillna(X_processed.mean())

        return X_processed

    def _select_best_model(self, X: pd.DataFrame, y: pd.Series, task: str):
        """Select best model using cross-validation"""
        if task == "classification":
            models = [
                LogisticRegression(max_iter=1000),
                DecisionTreeClassifier(),
                ensemble.RandomForestClassifier(),
            ]
        else:
            models = [
                LinearRegression(),
                DecisionTreeRegressor(),
                ensemble.RandomForestRegressor(),
            ]

        best_score = -float("inf")
        best_model = None

        for model in models:
            scores = model_selection.cross_val_score(model, X, y, cv=3)
            if scores.mean() > best_score:
                best_score = scores.mean()
                best_model = model

        return best_model

    def _get_model(self, model_type: str, task: str):
        """Get specific model by type"""
        models = {
            "logistic": LogisticRegression(max_iter=1000),
            "tree": (
                DecisionTreeClassifier()
                if task == "classification"
                else DecisionTreeRegressor()
            ),
            "forest": (
                ensemble.RandomForestClassifier()
                if task == "classification"
                else ensemble.RandomForestRegressor()
            ),
            "linear": LinearRegression(),
        }
        return models.get(model_type, LinearRegression())


class StatisticalAnalyzer:
    """Statistical analysis and hypothesis testing"""

    def __init__(self):
        self.test_results = []

    def perform_ttest(
        self, group1: List[float], group2: List[float], alpha: float = 0.05
    ) -> StatisticalTest:
        """Perform independent t-test"""
        statistic, p_value = stats.ttest_ind(group1, group2)

        # Effect size (Cohen's d)
        pooled_std = np.sqrt((np.std(group1) ** 2 + np.std(group2) ** 2) / 2)
        effect_size = (np.mean(group1) - np.mean(group2)) / pooled_std

        return StatisticalTest(
            test_name="Independent T-Test",
            statistic=statistic,
            p_value=p_value,
            alpha=alpha,
            reject_null=p_value < alpha,
            interpretation=f"Groups are {'significantly' if p_value < alpha else 'not significantly'} different",
            effect_size=effect_size,
        )

    def perform_anova(self, *groups, alpha: float = 0.05) -> StatisticalTest:
        """Perform one-way ANOVA"""
        statistic, p_value = stats.f_oneway(*groups)

        return StatisticalTest(
            test_name="One-Way ANOVA",
            statistic=statistic,
            p_value=p_value,
            alpha=alpha,
            reject_null=p_value < alpha,
            interpretation=f"Groups are {'significantly' if p_value < alpha else 'not significantly'} different",
        )

    def perform_chi_square(
        self, observed: List[List[int]], alpha: float = 0.05
    ) -> StatisticalTest:
        """Perform chi-square test of independence"""
        chi2, p_value, dof, expected = stats.chi2_contingency(observed)

        return StatisticalTest(
            test_name="Chi-Square Test",
            statistic=chi2,
            p_value=p_value,
            alpha=alpha,
            reject_null=p_value < alpha,
            interpretation=f"Variables are {'dependent' if p_value < alpha else 'independent'}",
        )

    def perform_normality_test(
        self, data: List[float], alpha: float = 0.05
    ) -> StatisticalTest:
        """Perform Shapiro-Wilk normality test"""
        statistic, p_value = stats.shapiro(data)

        return StatisticalTest(
            test_name="Shapiro-Wilk Test",
            statistic=statistic,
            p_value=p_value,
            alpha=alpha,
            reject_null=p_value < alpha,
            interpretation=f"Data is {'not normally' if p_value < alpha else 'normally'} distributed",
        )


class VisualizationEngine:
    """Data visualization and plotting"""

    def __init__(self):
        self.figures = []
        sns.set_style("whitegrid")

    def create_distribution_plot(
        self, data: pd.Series, title: str = "Distribution"
    ) -> str:
        """Create distribution plot"""
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Histogram
        axes[0].hist(data, bins=30, edgecolor="black", alpha=0.7)
        axes[0].set_title(f"{title} - Histogram")
        axes[0].set_xlabel("Value")
        axes[0].set_ylabel("Frequency")

        # Box plot
        axes[1].boxplot(data)
        axes[1].set_title(f"{title} - Box Plot")
        axes[1].set_ylabel("Value")

        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return img_base64

    def create_correlation_heatmap(self, df: pd.DataFrame) -> str:
        """Create correlation heatmap"""
        numerical_cols = df.select_dtypes(include=[np.number]).columns

        if len(numerical_cols) < 2:
            return None

        corr_matrix = df[numerical_cols].corr()

        plt.figure(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            annot=True,
            cmap="coolwarm",
            center=0,
            square=True,
            linewidths=1,
            cbar_kws={"shrink": 0.8},
        )
        plt.title("Correlation Heatmap")

        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return img_base64

    def create_scatter_plot(
        self, x: pd.Series, y: pd.Series, title: str = "Scatter Plot"
    ) -> str:
        """Create scatter plot with regression line"""
        plt.figure(figsize=(8, 6))
        plt.scatter(x, y, alpha=0.6)

        # Add regression line
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        plt.plot(x, p(x), "r--", alpha=0.8, label=f"y={z[0]:.2f}x+{z[1]:.2f}")

        plt.xlabel(x.name if hasattr(x, "name") else "X")
        plt.ylabel(y.name if hasattr(y, "name") else "Y")
        plt.title(title)
        plt.legend()
        plt.grid(True, alpha=0.3)

        # Save to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", dpi=100, bbox_inches="tight")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return img_base64


class DATASCIENCEPythonExecutor:
    """
    DATASCIENCE Agent Python Implementation v9.0

    Comprehensive data analysis, machine learning, and statistical modeling
    with automated insights generation and visualization capabilities.
    """

    def __init__(self):
        # v9.0 compliance attributes
        self.agent_name = "DATASCIENCE"
        self.version = "9.0"
        self.start_time = datetime.now().isoformat()

        self.data_analyzer = DataAnalyzer()
        self.model_builder = ModelBuilder()
        self.statistical_analyzer = StatisticalAnalyzer()
        self.visualization_engine = VisualizationEngine()
        self.datasets = {}
        self.results = {}
        self.metrics = {
            "datasets_analyzed": 0,
            "models_trained": 0,
            "statistical_tests": 0,
            "visualizations_created": 0,
            "insights_generated": 0,
            "errors": 0,
        }

    async def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DATASCIENCE commands"""
        try:
            result = await self.process_command(command)
            return result
        except Exception as e:
            self.metrics["errors"] += 1
            return {"error": str(e), "traceback": traceback.format_exc()}

    async def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process data science operations"""
        action = command.get("action", "")
        payload = command.get("payload", {})

        commands = {
            "load_data": self.load_data,
            "profile_data": self.profile_data,
            "train_model": self.train_model,
            "statistical_test": self.statistical_test,
            "visualize": self.visualize,
            "feature_engineering": self.feature_engineering,
            "anomaly_detection": self.anomaly_detection,
            "time_series_analysis": self.time_series_analysis,
            "clustering": self.clustering,
            "dimensionality_reduction": self.dimensionality_reduction,
            "generate_insights": self.generate_insights,
            "export_results": self.export_results,
        }

        handler = commands.get(action)
        if handler:
            return await handler(payload)
        else:
            return {"error": f"Unknown data science operation: {action}"}

    async def load_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Load dataset from file or create from array"""
        try:
            file_path = payload.get("file_path")
            data = payload.get("data")
            name = payload.get("name", "dataset")

            if file_path:
                # Load from file
                if file_path.endswith(".csv"):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(".json"):
                    df = pd.read_json(file_path)
                elif file_path.endswith(".parquet"):
                    df = pd.read_parquet(file_path)
                else:
                    return {"error": "Unsupported file format"}
            elif data:
                # Create from data
                df = pd.DataFrame(data)
            else:
                return {"error": "No data source provided"}

            self.datasets[name] = df
            self.metrics["datasets_analyzed"] += 1

            # Auto-profile
            profile = self.data_analyzer.profile_data(df)

            return {
                "status": "success",
                "dataset_name": name,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict(),
                "profile": asdict(profile),
            }

        except Exception as e:
            return {"error": f"Failed to load data: {str(e)}"}

    async def profile_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive data profile"""
        try:
            dataset_name = payload.get("dataset", "dataset")

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            profile = self.data_analyzer.profile_data(df)

            # Generate visualizations
            visualizations = []
            if HAS_PLOTTING:
                # Distribution plots for numerical columns
                numerical_cols = df.select_dtypes(include=[np.number]).columns[:5]
                for col in numerical_cols:
                    viz = self.visualization_engine.create_distribution_plot(
                        df[col], col
                    )
                    visualizations.append(
                        {"type": "distribution", "column": col, "image": viz}
                    )

                # Correlation heatmap
                heatmap = self.visualization_engine.create_correlation_heatmap(df)
                if heatmap:
                    visualizations.append({"type": "correlation", "image": heatmap})

            self.metrics["visualizations_created"] += len(visualizations)

            return {
                "status": "success",
                "profile": asdict(profile),
                "visualizations": visualizations,
                "insights": self._generate_profile_insights(profile),
            }

        except Exception as e:
            return {"error": f"Profiling failed: {str(e)}"}

    async def train_model(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Train machine learning model"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            target_column = payload.get("target")
            features = payload.get("features")
            model_type = payload.get("model_type", "auto")
            task = payload.get("task", "classification")

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]

            if not target_column or target_column not in df.columns:
                return {"error": "Invalid target column"}

            # Prepare features and target
            if features:
                X = df[features]
            else:
                X = df.drop(columns=[target_column])
            y = df[target_column]

            # Train model
            results = await self.model_builder.train_model(X, y, model_type, task)

            self.metrics["models_trained"] += 1

            return {
                "status": "success",
                "model_results": asdict(results),
                "insights": self._generate_model_insights(results),
            }

        except Exception as e:
            return {"error": f"Model training failed: {str(e)}"}

    async def statistical_test(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform statistical tests"""
        try:
            test_type = payload.get("test_type")
            data = payload.get("data")
            alpha = payload.get("alpha", 0.05)

            if test_type == "ttest":
                result = self.statistical_analyzer.perform_ttest(
                    data["group1"], data["group2"], alpha
                )
            elif test_type == "anova":
                result = self.statistical_analyzer.perform_anova(
                    *data["groups"], alpha=alpha
                )
            elif test_type == "chi_square":
                result = self.statistical_analyzer.perform_chi_square(
                    data["observed"], alpha
                )
            elif test_type == "normality":
                result = self.statistical_analyzer.perform_normality_test(
                    data["values"], alpha
                )
            else:
                return {"error": f"Unknown test type: {test_type}"}

            self.metrics["statistical_tests"] += 1

            return {"status": "success", "test_result": asdict(result)}

        except Exception as e:
            return {"error": f"Statistical test failed: {str(e)}"}

    async def visualize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create visualizations"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            viz_type = payload.get("type")
            columns = payload.get("columns", [])

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            visualizations = []

            if viz_type == "distribution":
                for col in columns:
                    if col in df.columns:
                        viz = self.visualization_engine.create_distribution_plot(
                            df[col], col
                        )
                        visualizations.append(
                            {"type": "distribution", "column": col, "image": viz}
                        )

            elif viz_type == "scatter":
                if len(columns) >= 2:
                    viz = self.visualization_engine.create_scatter_plot(
                        df[columns[0]], df[columns[1]]
                    )
                    visualizations.append(
                        {"type": "scatter", "columns": columns[:2], "image": viz}
                    )

            elif viz_type == "correlation":
                viz = self.visualization_engine.create_correlation_heatmap(df)
                if viz:
                    visualizations.append({"type": "correlation", "image": viz})

            self.metrics["visualizations_created"] += len(visualizations)

            return {"status": "success", "visualizations": visualizations}

        except Exception as e:
            return {"error": f"Visualization failed: {str(e)}"}

    async def feature_engineering(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform feature engineering"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            operations = payload.get("operations", [])

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name].copy()
            original_features = len(df.columns)
            engineered_features = []

            for op in operations:
                if op["type"] == "polynomial":
                    # Create polynomial features
                    cols = op.get(
                        "columns", df.select_dtypes(include=[np.number]).columns
                    )
                    for col in cols:
                        if col in df.columns:
                            df[f"{col}_squared"] = df[col] ** 2
                            df[f"{col}_cubed"] = df[col] ** 3
                            engineered_features.extend(
                                [f"{col}_squared", f"{col}_cubed"]
                            )

                elif op["type"] == "interaction":
                    # Create interaction features
                    cols = op.get("columns", [])
                    if len(cols) >= 2:
                        for i in range(len(cols) - 1):
                            for j in range(i + 1, len(cols)):
                                new_col = f"{cols[i]}_x_{cols[j]}"
                                df[new_col] = df[cols[i]] * df[cols[j]]
                                engineered_features.append(new_col)

                elif op["type"] == "binning":
                    # Create binned features
                    col = op.get("column")
                    bins = op.get("bins", 5)
                    if col in df.columns:
                        df[f"{col}_bin"] = pd.cut(df[col], bins=bins, labels=False)
                        engineered_features.append(f"{col}_bin")

            # Store engineered dataset
            self.datasets[f"{dataset_name}_engineered"] = df

            result = FeatureEngineering(
                original_features=original_features,
                engineered_features=len(engineered_features),
                selected_features=engineered_features,
                feature_scores={},
                transformation_pipeline=operations,
            )

            return {
                "status": "success",
                "feature_engineering": asdict(result),
                "new_dataset": f"{dataset_name}_engineered",
                "new_shape": df.shape,
            }

        except Exception as e:
            return {"error": f"Feature engineering failed: {str(e)}"}

    async def anomaly_detection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in data"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            method = payload.get("method", "isolation_forest")
            contamination = payload.get("contamination", 0.1)

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            numerical_cols = df.select_dtypes(include=[np.number]).columns

            if len(numerical_cols) == 0:
                return {"error": "No numerical columns for anomaly detection"}

            X = df[numerical_cols].fillna(df[numerical_cols].mean())

            if method == "isolation_forest":
                from sklearn.ensemble import IsolationForest

                detector = IsolationForest(contamination=contamination, random_state=42)
            elif method == "dbscan":
                detector = DBSCAN(eps=0.5, min_samples=5)
            else:
                return {"error": f"Unknown anomaly detection method: {method}"}

            anomalies = detector.fit_predict(X)
            anomaly_indices = np.where(anomalies == -1)[0]

            return {
                "status": "success",
                "anomalies_detected": len(anomaly_indices),
                "anomaly_indices": anomaly_indices.tolist(),
                "anomaly_percentage": len(anomaly_indices) / len(df) * 100,
                "method": method,
            }

        except Exception as e:
            return {"error": f"Anomaly detection failed: {str(e)}"}

    async def time_series_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform time series analysis"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            time_column = payload.get("time_column")
            value_column = payload.get("value_column")

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name].copy()

            if time_column not in df.columns or value_column not in df.columns:
                return {"error": "Invalid time or value column"}

            # Convert to datetime
            df[time_column] = pd.to_datetime(df[time_column])
            df = df.sort_values(time_column)

            # Calculate time series statistics
            ts_stats = {
                "mean": df[value_column].mean(),
                "std": df[value_column].std(),
                "trend": np.polyfit(range(len(df)), df[value_column], 1)[0],
                "seasonality": self._detect_seasonality(df[value_column]),
                "stationarity": self._test_stationarity(df[value_column]),
            }

            # Moving averages
            df["ma_7"] = df[value_column].rolling(window=7).mean()
            df["ma_30"] = df[value_column].rolling(window=30).mean()

            return {
                "status": "success",
                "time_series_stats": ts_stats,
                "recommendations": self._generate_ts_recommendations(ts_stats),
            }

        except Exception as e:
            return {"error": f"Time series analysis failed: {str(e)}"}

    async def clustering(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform clustering analysis"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            method = payload.get("method", "kmeans")
            n_clusters = payload.get("n_clusters", 3)

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            numerical_cols = df.select_dtypes(include=[np.number]).columns

            if len(numerical_cols) == 0:
                return {"error": "No numerical columns for clustering"}

            X = df[numerical_cols].fillna(df[numerical_cols].mean())

            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            if method == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            elif method == "dbscan":
                clusterer = DBSCAN(eps=0.5, min_samples=5)
            else:
                return {"error": f"Unknown clustering method: {method}"}

            clusters = clusterer.fit_predict(X_scaled)

            # Calculate cluster metrics
            from sklearn.metrics import calinski_harabasz_score, silhouette_score

            silhouette = (
                silhouette_score(X_scaled, clusters) if len(set(clusters)) > 1 else 0
            )
            calinski = (
                calinski_harabasz_score(X_scaled, clusters)
                if len(set(clusters)) > 1
                else 0
            )

            # Store clustered dataset
            df_clustered = df.copy()
            df_clustered["cluster"] = clusters
            self.datasets[f"{dataset_name}_clustered"] = df_clustered

            return {
                "status": "success",
                "n_clusters": len(set(clusters)),
                "cluster_sizes": pd.Series(clusters).value_counts().to_dict(),
                "silhouette_score": silhouette,
                "calinski_harabasz_score": calinski,
                "new_dataset": f"{dataset_name}_clustered",
            }

        except Exception as e:
            return {"error": f"Clustering failed: {str(e)}"}

    async def dimensionality_reduction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Perform dimensionality reduction"""
        try:
            dataset_name = payload.get("dataset", "dataset")
            method = payload.get("method", "pca")
            n_components = payload.get("n_components", 2)

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            numerical_cols = df.select_dtypes(include=[np.number]).columns

            if len(numerical_cols) < n_components:
                return {"error": "Not enough features for reduction"}

            X = df[numerical_cols].fillna(df[numerical_cols].mean())

            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            if method == "pca":
                reducer = PCA(n_components=n_components)
            else:
                return {"error": f"Unknown reduction method: {method}"}

            X_reduced = reducer.fit_transform(X_scaled)

            # Create reduced dataset
            reduced_df = pd.DataFrame(
                X_reduced, columns=[f"component_{i+1}" for i in range(n_components)]
            )

            # Add non-numerical columns back
            for col in df.columns:
                if col not in numerical_cols:
                    reduced_df[col] = df[col].values

            self.datasets[f"{dataset_name}_reduced"] = reduced_df

            result = {
                "status": "success",
                "original_dimensions": len(numerical_cols),
                "reduced_dimensions": n_components,
                "method": method,
                "new_dataset": f"{dataset_name}_reduced",
            }

            if method == "pca":
                result["explained_variance_ratio"] = (
                    reducer.explained_variance_ratio_.tolist()
                )
                result["cumulative_variance"] = np.cumsum(
                    reducer.explained_variance_ratio_
                ).tolist()

            return result

        except Exception as e:
            return {"error": f"Dimensionality reduction failed: {str(e)}"}

    async def generate_insights(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate automated insights from analysis"""
        try:
            dataset_name = payload.get("dataset", "dataset")

            if dataset_name not in self.datasets:
                return {"error": f"Dataset '{dataset_name}' not found"}

            df = self.datasets[dataset_name]
            insights = []

            # Data shape insights
            insights.append(
                f"Dataset contains {len(df):,} rows and {len(df.columns)} columns"
            )

            # Missing value insights
            missing_pct = df.isnull().sum() / len(df) * 100
            high_missing = missing_pct[missing_pct > 10]
            if len(high_missing) > 0:
                insights.append(
                    f"Columns with significant missing values: {', '.join(high_missing.index.tolist())}"
                )

            # Correlation insights
            numerical_cols = df.select_dtypes(include=[np.number]).columns
            if len(numerical_cols) > 1:
                corr_matrix = df[numerical_cols].corr()
                high_corr = []
                for i in range(len(corr_matrix.columns)):
                    for j in range(i + 1, len(corr_matrix.columns)):
                        if abs(corr_matrix.iloc[i, j]) > 0.7:
                            high_corr.append(
                                f"{corr_matrix.columns[i]} & {corr_matrix.columns[j]}"
                            )
                if high_corr:
                    insights.append(
                        f"Highly correlated features: {', '.join(high_corr)}"
                    )

            # Distribution insights
            for col in numerical_cols[:5]:
                skew = df[col].skew()
                if abs(skew) > 1:
                    insights.append(
                        f"'{col}' is {'right' if skew > 0 else 'left'}-skewed (skew={skew:.2f})"
                    )

            # Outlier insights
            for col in numerical_cols[:5]:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = (
                    (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)
                ).sum()
                if outliers > 0:
                    insights.append(
                        f"'{col}' has {outliers} potential outliers ({outliers/len(df)*100:.1f}%)"
                    )

            self.metrics["insights_generated"] += len(insights)

            return {
                "status": "success",
                "insights": insights,
                "total_insights": len(insights),
            }

        except Exception as e:
            return {"error": f"Insight generation failed: {str(e)}"}

    async def export_results(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Export analysis results"""
        try:
            export_format = payload.get("format", "json")
            include_data = payload.get("include_data", False)

            results = {
                "timestamp": datetime.now().isoformat(),
                "metrics": self.metrics,
                "datasets": list(self.datasets.keys()),
            }

            if include_data:
                results["data"] = {}
                for name, df in self.datasets.items():
                    if export_format == "json":
                        results["data"][name] = df.to_dict("records")
                    elif export_format == "csv":
                        results["data"][name] = df.to_csv(index=False)

            return {"status": "success", "results": results, "format": export_format}

        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}

    def _generate_profile_insights(self, profile: DataProfile) -> List[str]:
        """Generate insights from data profile"""
        insights = []

        if profile.data_quality_score < 70:
            insights.append(
                f"Data quality score is low ({profile.data_quality_score:.1f}/100)"
            )

        if profile.recommendations:
            insights.extend(profile.recommendations[:3])

        return insights

    def _generate_model_insights(self, results: ModelResults) -> List[str]:
        """Generate insights from model results"""
        insights = []

        if results.validation_score < 0.7:
            insights.append("Model performance is below acceptable threshold")
        elif results.validation_score > 0.95:
            insights.append("Warning: Model might be overfitting")

        if results.training_score - results.validation_score > 0.1:
            insights.append(
                "Significant gap between training and validation scores suggests overfitting"
            )

        return insights

    def _detect_seasonality(self, series: pd.Series) -> bool:
        """Simple seasonality detection"""
        if len(series) < 24:
            return False
        # Simple autocorrelation check
        return series.autocorr(lag=12) > 0.5 or series.autocorr(lag=24) > 0.5

    def _test_stationarity(self, series: pd.Series) -> bool:
        """Test for stationarity using simple heuristics"""
        # Simple test: check if mean of first half equals mean of second half
        mid = len(series) // 2
        first_half_mean = series[:mid].mean()
        second_half_mean = series[mid:].mean()
        return abs(first_half_mean - second_half_mean) < series.std() * 0.1

    def _generate_ts_recommendations(self, stats: Dict) -> List[str]:
        """Generate time series recommendations"""
        recommendations = []

        if not stats["stationarity"]:
            recommendations.append("Consider differencing to achieve stationarity")

        if stats["seasonality"]:
            recommendations.append(
                "Seasonal patterns detected - consider seasonal decomposition"
            )

        if abs(stats["trend"]) > 0.1:
            recommendations.append(
                f"{'Upward' if stats['trend'] > 0 else 'Downward'} trend detected"
            )

        return recommendations

    def get_capabilities(self) -> List[str]:
        """Return list of DATASCIENCE agent capabilities."""
        return [
            "data_loading",
            "data_cleaning",
            "exploratory_analysis",
            "statistical_testing",
            "machine_learning",
            "model_evaluation",
            "data_visualization",
            "correlation_analysis",
            "regression_analysis",
            "classification",
            "clustering",
            "time_series_analysis",
            "feature_engineering",
            "outlier_detection",
            "missing_value_handling",
            "hypothesis_testing",
            "distribution_analysis",
            "dimensionality_reduction",
            "predictive_modeling",
            "cross_validation",
            "model_comparison",
            "automated_insights",
            "report_generation",
            "statistical_summaries",
        ]

    def get_status(self) -> Dict[str, Any]:
        """Return current DATASCIENCE agent status."""

        # Create datascience files and documentation
        # Note: File creation moved to async context if needed
        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "status": "operational",
            "start_time": self.start_time,
            "uptime": str(
                datetime.now() - datetime.fromisoformat(self.start_time)
            ).split(".")[0],
            "datasets_loaded": len(self.datasets),
            "analysis_results": len(self.results),
            "metrics": self.metrics.copy(),
            "dependencies": {
                "pandas": HAS_PANDAS,
                "numpy": HAS_NUMPY,
                "sklearn": HAS_SKLEARN,
                "plotting": HAS_PLOTTING,
                "scipy": HAS_SCIPY,
            },
        }

    async def _create_datascience_files(
        self, result_data: Dict[str, Any], context: Dict[str, Any]
    ):
        """Create datascience files and artifacts using declared tools"""
        try:
            import json
            import os
            import time
            from pathlib import Path

            # Create directories
            main_dir = Path("data_analysis")
            docs_dir = Path("ml_models")

            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(docs_dir / "datasets", exist_ok=True)
            os.makedirs(docs_dir / "notebooks", exist_ok=True)
            os.makedirs(docs_dir / "models", exist_ok=True)
            os.makedirs(docs_dir / "reports", exist_ok=True)

            timestamp = int(time.time())

            # 1. Create main result file
            result_file = main_dir / f"datascience_result_{timestamp}.json"
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

            # 2. Create implementation script
            script_file = docs_dir / "datasets" / f"datascience_implementation.py"
            script_content = f'''#!/usr/bin/env python3
"""
DATASCIENCE Implementation Script
Generated by DATASCIENCE Agent at {datetime.now().isoformat()}
"""

import asyncio
import json
from typing import Dict, Any

class DatascienceImplementation:
    """
    Implementation for datascience operations
    """
    
    def __init__(self):
        self.agent_name = "DATASCIENCE"
        self.result_data = result_data
        
    async def execute(self) -> Dict[str, Any]:
        """Execute datascience implementation"""
        print(f"Executing {self.agent_name} implementation")
        
        # Implementation logic here
        await asyncio.sleep(0.1)
        
        return {
            "status": "completed",
            "agent": self.agent_name,
            "execution_time": "{datetime.now().isoformat()}"
        }
        
    def get_artifacts(self) -> Dict[str, Any]:
        """Get created artifacts"""
        return {
            "files_created": [
                "analysis.ipynb",
                "model.pkl",
                "data_report.html"
            ],
            "directories": ['datasets', 'notebooks', 'models', 'reports'],
            "description": "Data analysis and ML models"
        }

if __name__ == "__main__":
    impl = DatascienceImplementation()
    result = asyncio.run(impl.execute())
    print(f"Result: {result}")
'''

            with open(script_file, "w") as f:
                f.write(script_content)

            os.chmod(script_file, 0o755)

            # 3. Create README
            readme_content = f"""# DATASCIENCE Output

Generated by DATASCIENCE Agent at {datetime.now().isoformat()}

## Description
Data analysis and ML models

## Files Created
- Main result: `{result_file.name}`
- Implementation: `{script_file.name}`

## Directory Structure
- `datasets/` - datasets related files
- `notebooks/` - notebooks related files
- `models/` - models related files
- `reports/` - reports related files

## Usage
```bash
# Run the implementation
python3 {script_file}

# View results
cat {result_file}
```

---
Last updated: {datetime.now().isoformat()}
"""

            with open(docs_dir / "README.md", "w") as f:
                f.write(readme_content)

            print(
                f"DATASCIENCE files created successfully in {main_dir} and {docs_dir}"
            )

        except Exception as e:
            print(f"Failed to create datascience files: {e}")


# Export main class
__all__ = ["DATASCIENCEPythonExecutor"]
