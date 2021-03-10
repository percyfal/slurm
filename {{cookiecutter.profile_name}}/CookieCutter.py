#
# Based on lsf CookieCutter.py
#

class CookieCutter:

    SBATCH_DEFAULTS = "{{cookiecutter.sbatch_defaults}}"
    CLUSTER_NAME = "{{cookiecutter.cluster_name}}"
    CLUSTER_CONFIG = "{{cookiecutter.cluster_config}}"
    ADVANCED_ARGUMENT_CONVERSION = "{{cookiecutter.advanced_argument_conversion}}"

    @staticmethod
    def get_cluster_option() -> str:
        cluster = CookieCutter.CLUSTER_NAME
        if cluster != "":
            return f"--cluster={cluster}"
        return ""

    @staticmethod
    def get_advanced_argument_conversion() -> bool:
        val = {"yes": True, "no": False}[
            CookieCutter.ADVANCED_ARGUMENT_CONVERSION
        ]
        return val
