#
# Based on lsf CookieCutter.py
#

class CookieCutter:

    @staticmethod
    def get_sbatch_defaults() -> str:
        return "{{cookiecutter.sbatch_defaults}}"

    @staticmethod
    def get_cluster_name() -> str:
        return "{{cookiecutter.cluster_name}}"

    @staticmethod
    def get_cluster_option() -> str:
        cluster = CookieCutter.get_cluster_name()
        if cluster != "":
            return f"--cluster={cluster}"
        return ""

    @staticmethod
    def get_cluster_config() -> str:
        return "{{cookiecutter.cluster_config}}"

    @staticmethod
    def get_advanced_argument_conversion() -> bool:
        val = {"yes": True, "no": False}[
            "{{cookiecutter.advanced_argument_conversion}}"
        ]
        return val
