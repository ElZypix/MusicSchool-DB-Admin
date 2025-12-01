extern "C" {
    int calcular_edad_cpp(int dia_nac, int mes_nac, int anio_nac, int dia_act, int mes_act, int anio_act) {
        int edad = anio_act - anio_nac;

        if (mes_act < mes_nac || (mes_act == mes_nac && dia_act < dia_nac)) {
            edad--;
        }

        return edad;
    }
}