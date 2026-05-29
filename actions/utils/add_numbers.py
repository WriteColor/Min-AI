def add_numbers(parameters: dict, player=None):
    try:
        num1 = parameters.get("num1", 0)
        num2 = parameters.get("num2", 0)
        result = num1 + num2
        return f"La suma de {num1} y {num2} es: {result}"
    except Exception as e:
        return f"Error al ejecutar la función de suma: {e}"