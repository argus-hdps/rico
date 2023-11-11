/*
# This file is modified from part of the Astrometry.net suite, as packaged
# in astropy_healpix by NML, 2022. 
# Licensed under a 3-clause BSD style license - see LICENSE
*/

#include <stdbool.h>
#define DEG_PER_RAD 57.295779513082323

#ifndef MIN
#define	MIN(a,b) (((a)<(b))?(a):(b))
#endif
#ifndef MAX
#define	MAX(a,b) (((a)>(b))?(a):(b))
#endif

// Internal type
struct hp_s {
    int bighp;
    int x;
    int y;
};
typedef struct hp_s hp_t;

inline double xy2ra(double x, double y) {
    double a = atan2(y, x);
    if (a < 0)
        a += 2.0 * M_PI;
    return a;
}

inline double z2dec(double z) {
    return asin(z);
}

inline void xyz2radec(double x, double y, double z, double *ra, double *dec) {
    if (ra)
        *ra = xy2ra(x, y);
    if (dec) {
        if (fabs(z) > 0.9)
            *dec = M_PI / 2.0 - atan2(hypot(x, y), z);
        else
            *dec = z2dec(z);
    }
}

inline double rad2deg(double x) {
    return x * DEG_PER_RAD;
}

inline void xyzarr2radecdeg(const double* xyz, double *ra, double *dec) {
    xyz2radec(xyz[0], xyz[1], xyz[2], ra, dec);
    if (ra)
        *ra  = rad2deg(*ra);
    if (dec)
        *dec = rad2deg(*dec);
}


inline void swap_double(double* i1, double* i2) {
    double tmp;
    tmp = *i1;
    *i1 = *i2;
    *i2 = tmp;
}

inline bool ispolar(int healpix)
{
    // the north polar healpixes are 0,1,2,3
    // the south polar healpixes are 8,9,10,11
    return (healpix <= 3) || (healpix >= 8);
}

inline bool isequatorial(int healpix)
{
    // the north polar healpixes are 0,1,2,3
    // the south polar healpixes are 8,9,10,11
    return (healpix >= 4) && (healpix <= 7);
}

inline bool isnorthpolar(int healpix)
{
    return (healpix <= 3);
}

inline bool issouthpolar(int healpix)
{
    return (healpix >= 8);
}

static void hp_to_xyz(int Nside,
                    double dx, double dy, int chp, int xp, int yp, 
                    double* rx, double *ry, double *rz) {
    bool equatorial = true;
    double zfactor = 1.0;
    double x, y, z;
    double pi = M_PI, phi;
    double rad;

    // this is x,y position in the healpix reference frame
    x = xp + dx;
    y = yp + dy;

    if (isnorthpolar(chp)) {
        if ((x + y) > Nside) {
            equatorial = false;
            zfactor = 1.0;
        }
    }
    if (issouthpolar(chp)) {
        if ((x + y) < Nside) {
            equatorial = false;
            zfactor = -1.0;
        }
    }

    if (equatorial) {
        double zoff=0;
        double phioff=0;
        x /= (double)Nside;
        y /= (double)Nside;

        if (chp <= 3) {
            // north
            phioff = 1.0;
        } else if (chp <= 7) {
            // equator
            zoff = -1.0;
            chp -= 4;
        } else if (chp <= 11) {
            // south
            phioff = 1.0;
            zoff = -2.0;
            chp -= 8;
        } else {
            // should never get here
            assert(0);
        }

        z = 2.0/3.0*(x + y + zoff);
        phi = pi/4*(x - y + phioff + 2*chp);
        rad = sqrt(1.0 - z*z);

    } else {
        double phi_t;
        double vv;

        if (zfactor == -1.0) {
            swap_double(&x, &y);
            x = (Nside - x);
            y = (Nside - y);
        }

        if (y == Nside && x == Nside)
            phi_t = 0.0;
        else
            phi_t = pi * (Nside-y) / (2.0 * ((Nside-x) + (Nside-y)));

        if (phi_t < pi/4.) {
            vv = fabs(pi * (Nside - x) / ((2.0 * phi_t - pi) * Nside) / sqrt(3));
        } else {
            vv = fabs(pi * (Nside-y) / (2. * phi_t * Nside) / sqrt(3));
        }
        z = (1 - vv) * (1 + vv);
        rad = sqrt(1.0 + z) * vv;

        z *= zfactor;

        // The big healpix determines the phi offset
        if (issouthpolar(chp))
            phi = pi/2.0* (chp-8) + phi_t;
        else
            phi = pi/2.0 * chp + phi_t;
    }

    if (phi < 0.0)
        phi += 2*pi;

    *rx = rad * cos(phi);
    *ry = rad * sin(phi);
    *rz = z;
}

long int healpixl_nested_to_xy(long int hp, int Nside) {
    int bighp, x, y;
    long int index;
    long int ns2 = (int64_t)Nside * (int64_t)Nside;
    int i;

    bighp = (int)(hp / ns2);
    index = hp % ns2;
    x = y = 0;
    for (i=0; i<(signed int) (8*sizeof(long int)/2); i++) {
        x |= (index & 0x1) << i;
        index >>= 1;
        y |= (index & 0x1) << i;
        index >>= 1;
        if (!index) break;
    }
    return ((((long int)bighp * (long int)Nside) + x) * (long int)Nside) + y;    
}

// assumes nested order
void healpixl_grid_to_radecdeg(long int healpix, int n_points, int Nside, double* dx, double* dy, double* ra, double* dec)
{                        
    double xyz[3];
    long int h = healpixl_nested_to_xy(healpix, Nside);
    long int ns2 = (long int)Nside * (long int)Nside;
    int bighp = (int)(h / ns2);
    long int hp = h % ns2;
    int px = (int)(hp / Nside);
    int py = hp % Nside;

    for (int i=0;i<n_points;i++)
    {
        hp_to_xyz(Nside, dx[i], dy[i], bighp, px, py, xyz, xyz+1, xyz+2);
        xyzarr2radecdeg(xyz, ra + i, dec + i);
    }
}

void healpixls_to_radecdeg(long int *ihp, int n_hpxes, int Nside, double dx, double dy, 
                        double* ra, double* dec) 
{                        
    double xyz[3];

    for (int i=0;i<n_hpxes;i++)
    {
        long int h = healpixl_nested_to_xy(ihp[i], Nside);

        long int ns2 = (long int)Nside * (long int)Nside;
        int bighp = (int)(h / ns2);
        long int hp = h % ns2;
        int px = (int)(hp / Nside);
        int py = hp % Nside;

        hp_to_xyz(Nside, dx, dy, bighp, px, py, xyz, xyz+1, xyz+2);
        xyzarr2radecdeg(xyz, ra + i, dec + i);
    }
}

// assumes nested order
void healpixl_to_radecdeg(long int hp_in, int Nside, double dx, double dy, 
                        double* ra, double* dec) 
{                        
    double xyz[3];

    long int h = healpixl_nested_to_xy(hp_in, Nside);

    long int ns2 = (long int)Nside * (long int)Nside;
    int bighp = (int)(h / ns2);
    long int hp = h % ns2;
    int px = (int)(hp / Nside);
    int py = hp % Nside;

    hp_to_xyz(Nside, dx, dy, bighp, px, py, xyz, xyz+1, xyz+2);
    xyzarr2radecdeg(xyz, ra, dec);
}

hp_t xyztohp(double vx, double vy, double vz, double coz, int Nside) {
    double phi;
    double twothirds = 2.0 / 3.0;
    double pi = M_PI;
    double twopi = 2.0 * M_PI;
    double halfpi = 0.5 * M_PI;
    double root3 = sqrt(3.0);
    int basehp;
    int x, y;
    double sector;
    int offset;
    double phi_t;
    hp_t hp;

    /* Convert our point into cylindrical coordinates for middle ring */
    phi = atan2(vy, vx);
    if (phi < 0.0)
        phi += twopi;
    phi_t = fmod(phi, halfpi);

    // North or south polar cap.
    if ((vz >= twothirds) || (vz <= -twothirds)) {
        bool north;
        int column;
        double xx, yy, kx, ky;

        // Which pole?
        if (vz >= twothirds) {
            north = true;
        } else {
            north = false;
            vz *= -1.0;
        }

        // if not passed, compute coz
        if (coz == 0.0)
            coz = hypot(vx, vy);

        // solve eqn 20: k = Ns - xx (in the northern hemi)
        kx = (coz / sqrt(1.0 + vz)) * root3 * fabs(Nside * (2.0 * phi_t - pi) / pi);

        // solve eqn 19 for k = Ns - yy
        ky = (coz / sqrt(1.0 + vz)) * root3 * Nside * 2.0 * phi_t / pi;

        if (north) {
            xx = Nside - kx;
            yy = Nside - ky;
        } else {
            xx = ky;
            yy = kx;
        }

        // xx, yy should be in [0, Nside].
        x = MIN(Nside-1, floor(xx));

        y = MIN(Nside-1, floor(yy));

        sector = (phi - phi_t) / (halfpi);
        offset = (int)round(sector);

        offset = ((offset % 4) + 4) % 4;

        column = offset;

        if (north)
            basehp = column;
        else
            basehp = 8 + column;

    } else {
        // could be polar or equatorial.
        double sector;
        int offset;
        double u1, u2;
        double zunits, phiunits;
        double xx, yy;

        // project into the unit square z=[-2/3, 2/3], phi=[0, pi/2]
        zunits = (vz + twothirds) / (4.0 / 3.0);
        phiunits = phi_t / halfpi;
        // convert into diagonal units
        // (add 1 to u2 so that they both cover the range [0,2].
        u1 = zunits + phiunits;
        u2 = zunits - phiunits + 1.0;

        // x is the northeast direction, y is the northwest.
        xx = u1 * Nside;
        yy = u2 * Nside;

        // now compute which big healpix it's in.
        // (note that we subtract off the modded portion used to
        // compute the position within the healpix, so this should be
        // very close to one of the boundaries.)
        sector = (phi - phi_t) / (halfpi);
        offset = (int)round(sector);
        assert(fabs(sector - offset) < EPS);
        offset = ((offset % 4) + 4) % 4;

        // we're looking at a square in z,phi space with an X dividing it.
        // we want to know which section we're in.
        // xx ranges from 0 in the bottom-left to 2Nside in the top-right.
        // yy ranges from 0 in the bottom-right to 2Nside in the top-left.
        // (of the phi,z unit box)
        if (xx >= Nside) {
            xx -= Nside;
            if (yy >= Nside) {
                // north polar.
                yy -= Nside;
                basehp = offset;
            } else {
                // right equatorial.
                basehp = ((offset + 1) % 4) + 4;
            }
        } else {
            if (yy >= Nside) {
                // left equatorial.
                yy -= Nside;
                basehp = offset + 4;
            } else {
                // south polar.
                basehp = 8 + offset;
            }
        }

        x = MAX(0, MIN(Nside-1, floor(xx)));
        y = MAX(0, MIN(Nside-1, floor(yy)));
    }

    hp.bighp = basehp;
    hp.x = x;
    hp.y = y;

    return hp;
}

#define radec2x(r,d) (cos(d)*cos(r))
#define radec2y(r,d) (cos(d)*sin(r))
#define radec2z(r,d) (sin(d))

long int radec_to_healpixl(double ra, double dec, int Nside) {
    ra = ra / DEG_PER_RAD;
    dec = dec / DEG_PER_RAD;

    hp_t hp = xyztohp(radec2x(ra,dec), radec2y(ra,dec),
                    radec2z(ra,dec), cos(dec), Nside);

    long int index = 0;
    long int ns2 = (long int)Nside * (long int)Nside;
    int x = hp.x;
    int y = hp.y;

    for (int i=0; i<(8*(int)sizeof(int64_t)/2); i++) {
        index |= (int64_t)(((y & 1) << 1) | (x & 1)) << (i*2);
        y >>= 1;
        x >>= 1;
        if (!x && !y) break;
    }

    return index + (long int)hp.bighp * ns2;
}

void radecs_to_healpixls(double *ra, double *dec, int n_points, long int *hpixes, int Nside) {
    for (int i=0;i<n_points;i++)
    {
        hpixes[i] = radec_to_healpixl(ra[i], dec[i], Nside);
    }
}
