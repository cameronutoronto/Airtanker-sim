double to_rad(double degrees);
double to_degrees(double radians);
double distance(double x1, double y1, double x2, double y2);
double perimeter_ellipse(double a, double b);
double ellipse_radius(double a, double b, double theta);
double area_ellipse(double major, double minor);
double get_bearing(double x1, double y1, double x2, double y2);
double translate_coordinate_lat(double lon, double lat, double theta, double d_r);
double translate_coordinate_lon(double lon, double lat, double theta, double d_r, double new_lat);