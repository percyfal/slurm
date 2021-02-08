#
# Based on lsf CookieCutter.py
#

class CookieCutter:

    @staticmethod
    def get_sbatch_defaults() -> str:
        defaults = "{{cookiecutter.sbatch_defaults}}"
        cluster = CookieCutter.get_cluster_name()
        if cluster != "":
            defaults = defaults + f" --cluster={cluster}"
        return defaults

    @staticmethod
    def get_cluster_name() -> str:
        return "{{cookiecutter.cluster_name}}"

    # To be deprecated in favor of local slurm.yaml file
    @staticmethod
    def get_cluster_config() -> str:
        return "{{cookiecutter.cluster_config}}"

    @staticmethod
    def get_advanced_argument_conversion() -> bool:
        val = {"yes": True, "no": False}[
            "{{cookiecutter.advanced_argument_conversion}}"
        ]
        return val
