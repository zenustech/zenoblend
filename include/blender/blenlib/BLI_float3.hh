/*
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software Foundation,
 * Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 */

#pragma once

#include <iostream>

namespace blender {

struct float3 {
  float x, y, z;

  float3() = default;

  float3(const float *ptr) : x{ptr[0]}, y{ptr[1]}, z{ptr[2]}
  {
  }

  float3(const float (*ptr)[3]) : float3(static_cast<const float *>(ptr[0]))
  {
  }

  explicit float3(float value) : x(value), y(value), z(value)
  {
  }

  explicit float3(int value) : x(value), y(value), z(value)
  {
  }

  float3(float x, float y, float z) : x{x}, y{y}, z{z}
  {
  }

  operator const float *() const
  {
    return &x;
  }

  operator float *()
  {
    return &x;
  }

  friend float3 operator+(const float3 &a, const float3 &b)
  {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
  }

  float3 &operator+=(const float3 &b)
  {
    this->x += b.x;
    this->y += b.y;
    this->z += b.z;
    return *this;
  }

  friend float3 operator-(const float3 &a, const float3 &b)
  {
    return {a.x - b.x, a.y - b.y, a.z - b.z};
  }

  friend float3 operator-(const float3 &a)
  {
    return {-a.x, -a.y, -a.z};
  }

  float3 &operator-=(const float3 &b)
  {
    this->x -= b.x;
    this->y -= b.y;
    this->z -= b.z;
    return *this;
  }

  float3 &operator*=(float scalar)
  {
    this->x *= scalar;
    this->y *= scalar;
    this->z *= scalar;
    return *this;
  }

  float3 &operator*=(const float3 &other)
  {
    this->x *= other.x;
    this->y *= other.y;
    this->z *= other.z;
    return *this;
  }

  friend float3 operator*(const float3 &a, const float3 &b)
  {
    return {a.x * b.x, a.y * b.y, a.z * b.z};
  }

  friend float3 operator*(const float3 &a, float b)
  {
    return {a.x * b, a.y * b, a.z * b};
  }

  friend float3 operator*(float a, const float3 &b)
  {
    return b * a;
  }

  friend float3 operator/(const float3 &a, float b)
  {
    //BLI_assert(b != 0.0f);
    return {a.x / b, a.y / b, a.z / b};
  }

  friend std::ostream &operator<<(std::ostream &stream, const float3 &v)
  {
    stream << "(" << v.x << ", " << v.y << ", " << v.z << ")";
    return stream;
  }

  friend bool operator==(const float3 &a, const float3 &b)
  {
    return a.x == b.x && a.y == b.y && a.z == b.z;
  }

  friend bool operator!=(const float3 &a, const float3 &b)
  {
    return !(a == b);
  }
};

}  // namespace blender
