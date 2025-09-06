import { React, useEffect, useState } from "react";
import { logout, useNumCredits } from "../redux/UserSlice";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  accountPath,
  apiKeyDashboardPath,
  downloadPrivateGPTPath,
  landing,
} from "../constants/RouteConstants";
import { Dropdown, Navbar, Avatar } from "flowbite-react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faCoins } from "@fortawesome/free-solid-svg-icons";
import { useLocation } from "react-router-dom";
import { useUser, viewUser } from "../redux/UserSlice";
import LoginModal from "./LoginModal";

// function MainNav(props) {
//   let dispatch = useDispatch();
//   let navigate = useNavigate();
//   let user = useUser();
//   console.log("user", user);
//   let numCredits = useNumCredits();

//   useEffect(() => {
//     dispatch(viewUser());
//   }, []);

//   // useEffect(() => {
//   //   if (user && "id" in user) {
//   //     // Start polling when the component mounts
//   //     const intervalId = setInterval(() => {
//   //       // dispatch(refreshCredits());
//   //     }, 5000); // Poll every 5 seconds

//   //     // Clear the polling interval when the component unmounts
//   //     return () => clearInterval(intervalId);
//   //   }
//   // }, [user]);

//   var imageUrl = null;
//   if (user && "profile_pic_url" in user) {
//     imageUrl = user["profile_pic_url"];
//   }

//   return (
//     <Navbar className="fixed w-full z-50 bg-anoteblack-800" fluid>
//       {/* <Navbar.Brand href="https://privatechatbot.ai"> */}
//       <Navbar.Brand onClick={() => navigate(landing)}>
//         <div className="h-8 w-8 bg-center bg-contain bg-[url('../public/logonew.png')] dark:bg-[url('../public/logonew.png')]"></div>
//         <span className="self-center md:block hidden whitespace-nowrap text-lg font-semibold text-white pl-2">
//           Panacea
//         </span>
//       </Navbar.Brand>
//       <div className="flex items-center md:order-2">
//         <div
//           className="mr-3 my-1 py-1 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-2xl cursor-pointer"
//           onClick={() => navigate(downloadPrivateGPTPath)}
//         >
//           <span className="px-3 text-xs font-bold text-black">
//             <FontAwesomeIcon icon={faCoins} className="mr-1" />
//             Download Private Version
//           </span>
//         </div>
//         <Dropdown
//           theme={{
//             arrowIcon: "text-white ml-2 h-4 w-4",
//           }}
//           className="bg-gray-950 text-white"
//           inline
//           label={
//             imageUrl == "" ? (
//               <Avatar rounded />
//             ) : (
//               <Avatar img={imageUrl} rounded />
//             )
//           }
//         >
//           <Dropdown.Header>
//             {user && user.name && (
//               <span className="block text-sm text-white">{user.name}</span>
//             )}
//             <span className="block truncate text-sm font-medium text-white hover:bg-[#141414]">
//               {numCredits} Credits Remaining
//               <FontAwesomeIcon icon={faCoins} className="ml-2" />
//             </span>
//           </Dropdown.Header>
//           <Dropdown.Item
//             onClick={() => navigate(accountPath)}
//             className="text-white hover:text-black"
//           >
//             Account
//           </Dropdown.Item>
//           <Dropdown.Item
//             onClick={() => navigate(apiKeyDashboardPath)}
//             className="text-white hover:text-black"
//           >
//             API
//           </Dropdown.Item>
//           <Dropdown.Divider />
//           <Dropdown.Item
//             onClick={() =>
//               dispatch(logout()).then(() => {
//                 navigate("/");
//                 props.setIsLoggedInParent(false);
//               })
//             }
//             className="text-white hover:text-black"
//           >
//             Sign out
//           </Dropdown.Item>
//         </Dropdown>
//       </div>
//     </Navbar>
//   );
// }

export function MainNav({ isLoggedIn, setIsLoggedInParent }) {
  const [showLoginModal, setShowLoginModal] = useState();
  let user = useUser();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  let numCredits = useNumCredits();
  let imageUrl = null;
  if (user && "profile_pic_url" in user) {
    imageUrl = user["profile_pic_url"];
  }
  
  function handleLogout() {
    dispatch(logout()).then(() => {
      navigate("/");
      setIsLoggedInParent(false);
    });
  }

  return (
    <div className="fixed z-50 flex items-center justify-between w-full px-2 py-4 text-white">
      {showLoginModal && (
        <LoginModal
          onClose={() => setShowLoginModal((p) => !p)}
          isOpen={showLoginModal}
        />
      )}
      <div className="flex  items-center">
        <img alt="pancea logo" width={30} height={30} src="/logonew.png" />
        <span className="self-center whitespace-nowrap text-lg font-semibold text-white pl-2">
          Panacea
        </span>
      </div>
      <button
        onClick={() => setShowLoginModal(true)}
        className={`py-2 ${
          isLoggedIn && "hidden"
        } px-4 bg-gradient-to-r from-[#EDDC8F] to-[#F1CA57] text-black rounded-lg font-medium hover:opacity-90 transition-opacity`}
      >
        Log In
      </button>
      <div className={!isLoggedIn && "hidden"}>
        <Dropdown
          theme={{
            arrowIcon: "text-white ml-2 h-4 w-4",
          }}
          className={`bg-gray-950 text-white`}
          inline
          label={
            imageUrl === "" ? (
              <Avatar rounded />
            ) : (
              <Avatar img={imageUrl} rounded />
            )
          }
        >
          <Dropdown.Header>
            {user && user.name && (
              <span className="block text-sm text-white">{user.name}</span>
            )}
            <span className="block truncate text-sm font-medium text-white hover:bg-[#141414]">
              {numCredits} Credits Remaining
              <FontAwesomeIcon icon={faCoins} className="ml-2" />
            </span>
          </Dropdown.Header>
          <Dropdown.Item
            onClick={() => navigate(accountPath)}
            className="text-white hover:text-black"
          >
            Account
          </Dropdown.Item>
          <Dropdown.Item
            onClick={() => navigate(apiKeyDashboardPath)}
            className="text-white hover:text-black"
          >
            API
          </Dropdown.Item>
          <Dropdown.Divider />
          <Dropdown.Item
            onClick={() => handleLogout()}
            className="text-white hover:text-black"
          >
            Sign out
          </Dropdown.Item>
        </Dropdown>
      </div>
    </div>
  );
}

export default MainNav;
