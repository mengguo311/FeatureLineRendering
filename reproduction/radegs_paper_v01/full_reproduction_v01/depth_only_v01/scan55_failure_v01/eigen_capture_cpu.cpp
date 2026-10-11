// CPU-only reproduction of the actual captured, finite SPD covariance.
#include <iostream>
#include <fstream>
#include <iomanip>
#include <cmath>
#include "paper_geometry_precision.cuh"
int main(int argc,char** argv){
  if(argc!=2)return 2;
  std::ifstream input(argv[1]);glm::mat3 A;
  for(int r=0;r<3;++r)for(int c=0;c<3;++c)input>>A[c][r];
  if(!input)return 3;
  glm::vec3 e;glm::mat3 U;auto n=paper_find_eigenvalues(A,e,U);
  std::cout<<std::setprecision(17)<<"count "<<n<<" values "<<e.x<<" "<<e.y<<" "<<e.z<<"\n";
  float maxerr=0,maxa=0;
  auto rec=U*glm::mat3(e.x,0,0,0,e.y,0,0,0,e.z)*glm::transpose(U);
  for(int r=0;r<3;++r){for(int c=0;c<3;++c){std::cout<<U[c][r]<<" "; maxerr=std::max(maxerr,std::abs(rec[c][r]-A[c][r]));maxa=std::max(maxa,std::abs(A[c][r]));}std::cout<<"\n";}
  std::cout<<"relative_reconstruction_error "<<maxerr/maxa<<"\n";
  bool pass=n==3 && std::isfinite(maxerr/maxa) && maxerr/maxa<1e-5 && e.x>1e-8 && e.y>1e-8 && e.z>1e-8;
  std::cout<<(pass?"PASS":"FAIL")<<" captured covariance spectral decomposition\n";return pass?0:1;
}
