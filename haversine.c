#include<math.h>
//#include<stdio.h>
#ifndef M_PI
#define M_PI 3.1415926535897932384626433832795028841971693
#endif

/*double abs(double a){
	if (a >=0) return a;
	return -1.0 * a;

}*/

double to_rad(double degrees){
//Convert a number to radians
return degrees * M_PI / 180.0;}

double to_degrees(double radians){
return radians * 180.0 / M_PI;}

double area_ellipse(double major, double minor){
return M_PI * major * minor;}

double get_bearing(double x1, double y1, double x2, double y2){
x1 = to_rad(x1);
x2 = to_rad(x2);
y1 = to_rad(y1);
y2 = to_rad(y2);
return atan2(sin(x2 - x1) * cos(y2), cos(y1) * sin(y2) - sin(y1) * cos(y2) * cos(x2 - x1));}

double translate_coordinate_lat(double lon, double lat, double theta, double d_r){
lon = to_rad(lon);
lat = to_rad(lat);
return asin(sin(lat) * cos(d_r) + cos(lat) * sin(d_r) * cos(theta));}

double translate_coordinate_lon(double lon, double lat, double theta, double d_r, double new_lat){
lon = to_rad(lon);
lat = to_rad(lat);
return lon + atan2(sin(theta) * sin(d_r) * cos(lat), cos(d_r) - sin(lat) * sin(new_lat));}


double distance(double x1, double y1, double x2, double y2){
//Uses haversine formula from Source: http://en.wikipedia.org/wiki/Haversine_formula to calculate distance
double lat_diff_2 = (to_rad(y2) - to_rad(y1)) / 2.0;
double long_diff_2 = (to_rad(x2) - to_rad(x1)) / 2.0;
double const_val = 2.0 * 6371.0;
return const_val * asin(sqrt(sin(lat_diff_2) * sin(lat_diff_2) + (cos(to_rad(y1)) * cos(to_rad(y2)) * sin(long_diff_2) * sin(long_diff_2))));
}

double perimeter_ellipse(double a, double b){
//a is major axis b is minor axis
if (a == 0.0 || b == 0.0) return 0.0;
double h = ((a - b) * (a - b)) / ((a + b) * (a + b));
return M_PI * (a + b) * (1 + (3 * h) / (10 + sqrt(4 - 3 * h)));}

double ellipse_radius(double a, double b, double theta){
if (a == 0.0 || b == 0.0) return 0.0;
return a * b / (sqrt((b * cos(theta)) * (b * cos(theta)) + (a * sin(theta)) * (a * sin(theta))));}

double minor_axis(double a, double theta, double radius)
{
	if (theta == M_PI || theta == 0 || theta == 2 * M_PI ) return 0.0;
	double constant1 = radius * radius / (a * a);
	double constant2 = a * sin(theta) * a * sin(theta);
	return sqrt((-1.0 * constant1 * constant2) / (constant1 * cos(theta) * cos(theta) - 1.0));

}

//int main(){ printf("%lf", minor_axis(10, M_PI * 3 / 2, 3));}



/*int main(){
double y1 = 43.7, x1 = -79.4, y2 = 49.25, x2 = -123.1;
double dist = distance(x1, y1, x2, y2);
printf("Distance is %f\n", dist);
double a = 10, b = 4;
double perim = perimeter_ellipse(a, b);
printf("Peimeter: %f\n", perim);
double radius = ellipse_radius(a, b, M_PI / 2);
printf("Radius: %f\n", radius);} */

